import logging
from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional, Sequence, Union

from lxml import etree

from . import FILL_TOKEN, PT_NS, __project__
from .exc import PTEvalError, PTFetchError, PTTemplateError
from .extensions import ExtensionManager
from .extensions.pt import context
from .label_tools import (
    ATTR_PATHS,
    LabelLike,
    PathManipulator,
    add_default_ns,
    is_populated,
    labellike_to_etree,
)
from .state import PTState, SourceGroup


class Template:
    """The `Template` class manages the creation of a data product from a type template.

    After instantiation, the partial label is available through the `label` attribute.
    For convenience, the document `root` is also exposed, together with its `nsmap`
    (the namespace prefix->uri dictionary of the partial label).

    Attributes:
        label lxml.etree._ElementTree: The partial label represented as an lxml element
            tree, which allows access to its classes and attributes via the XML DOM.
        root lxml.etree._Element: The partial label's root element (e.g.
            `Product_Observational`)
        nsmap dict: The partial label's namespace map
    """

    def __init__(
        self,
        template: LabelLike,
        source_map: Dict[str, Union[LabelLike, Sequence[LabelLike]]],
        context_map: Optional[dict] = None,
        template_source_entry: bool = True,
        keep_template_comments: bool = False,
        skip_structure_check: bool = False,
        quiet: Union[bool, int] = False,
    ):
        """Instantiate a partial label from the provided type template.

        Run the provided `template` through a series of pre-processing steps resulting
        in a partial label.

        Args:
            template: `LabelLike` representation of the output product's type template
                (e.g. a string path to an XML file).
            source_map: A dictionary which maps string monikers used by the `pt:sources`
                property, to `LabelLike` source products. A single moniker can map to a
                single product or a list of products, and products can be referenced by
                multiple monikers. For instance:
                ```python
                    {
                        "input": "input.xml",
                        "flat": "flatfield.xml",
                        "processing_inputs": [
                            "input.xml",
                            "flatfield.xml"
                        ],
                    }
                ```
            context_map: If called for by the template, a dictionary of key-value pairs
                which can be looked up using the `pt:context()` XPath extension
                function, for instance to automatically populate history entries with
                the processor's ID and version using the `pt:fill` property.
            template_source_entry: Add a "template"->`template` mapping to `source_map`.
                Convenience option for self-referencing templates.
            keep_template_comments: If enabled, propagate XML comments from `template`
                to the exported output product.
            skip_structure_check: If enabled, share a few milliseconds off the export
                process (and some kilobytes of memory) by not sanity-checking the
                structure of the partial label to that of the original `template`.
            quiet: If set to True, suppress `Template` log messages below logging.ERROR
                from propagating up the hierarchy. Alternatively, a numeric log level
                can be provided, which will be forwarded directly to the `Template`
                logger.
        """

        log_level = (
            (logging.ERROR if quiet else logging.INFO)
            if isinstance(quiet, bool)
            else quiet  # custom log level provided
        )
        logging.getLogger(__project__).setLevel(log_level)
        self._log = logging.getLogger(".".join([__project__, self.__class__.__name__]))

        self._sources = self._source_map_to_etree_map(source_map)
        try:
            self.label = labellike_to_etree(template)
        except TypeError as e:
            raise TypeError(f"template is in an {e}") from None
        if template_source_entry:
            if "template" in self._sources:
                raise KeyError(
                    "source map already contains a mapping for the key 'template'"
                )
            self._sources["template"] = self.label

        if not keep_template_comments:
            etree.strip_elements(self.label, etree.Comment, with_tail=False)

        self.root = self.label.getroot()
        self.nsmap = add_default_ns(self.root.nsmap)

        context.set_context_map(context_map)
        self._ext = ExtensionManager()

        self._deferred_fills = []
        self._deferred_reqs = []

        self._process_elem(
            PTState(parent=None, t_elem=None, source_map=self._sources), self.root
        )

        self._label_pre_handoff = None if skip_structure_check else deepcopy(self.label)

    def export(
        self, directory: Union[Path, str], filename: Optional[str] = None
    ) -> None:
        """Export the partial label to the filesystem.

        Run the partial label through a series of post-processing steps before exporting
        the completed label to `filename` in `directory.

        If `filename` is not provided, the product ID part of the post-processed label's
        logical identifier (LID) will be used. Please note that this behaviour is
        likely to change in an upcoming release!

        Args:
            directory: Path to the desired output directory.
            filename: Filename override to use for the output label.
        """
        self._eval_deferred_fills()
        self._prune_empty_optionals()
        self._ensure_populated()
        self._check_structure()
        etree.cleanup_namespaces(self.label)
        if filename is None:
            lid = self.label.xpath(ATTR_PATHS["lid"], namespaces=self.nsmap)[0].text
            filename = f"{lid.split(':')[-1].strip()}.xml"  # ExoMars/PSA specific
        if not isinstance(directory, Path):
            directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.label.write(
            str(directory / filename),
            encoding="UTF-8",
            pretty_print=True,
            xml_declaration=True,
        )

    def _source_map_to_etree_map(
        self, smap: Dict[str, Union[LabelLike, Sequence[LabelLike]]]
    ):
        cache = {}
        for key in smap:
            if key in cache:
                smap[key] = cache[key]
            else:
                try:
                    if isinstance(
                        smap[key], LabelLike.__args__
                    ):  # FIXME: __args__ is undocumented (= not reliable)
                        smap[key] = cache[key] = labellike_to_etree(smap[key])
                    else:
                        smap[key] = cache[key] = [
                            labellike_to_etree(ll) for ll in smap[key]
                        ]
                except TypeError as e:
                    raise TypeError(f"source map key {key} maps to an {e}") from None
        return smap

    def _process_elem(self, parent_state: PTState, t_elem: etree._Element):
        if isinstance(t_elem, etree._Comment):
            return
        self._ext.set_elem_context(t_elem)
        qname = etree.QName(t_elem.tag)
        state = PTState(parent_state, t_elem)

        # duplicate subtree for each source
        if len(state["sources"].secondary):
            # prevent triggering this processing branch on sibling passes
            del t_elem.attrib[self._pt_clark("sources")]
            # We temporarily detach the t_elem subtree and insert each elem subtree at
            # the original location of t_elem before populating, which ensures that
            # resolved paths are always in the form /path/to/elem[1]/child, which will
            # match corresponding source elements (e.g. /path/to/elem/child) in the
            # multi source fetch scenario. Caveat: downstream deferred pt:fill or
            # pt:required will be evaluated in the context of their element's final
            # path (e.g. /path/to/elem[3]/child).
            #
            # Inserting and populating the subtrees in reverse order ensures that their
            # final document order for multi source fetches is aligned with the order of
            # the source_map sources.
            parent = t_elem.getparent()
            idx = parent.index(t_elem)
            parent.remove(t_elem)
            for source in reversed(
                (state["sources"].primary, *state["sources"].secondary)
            ):
                elem = (
                    t_elem if source is state["sources"].primary else deepcopy(t_elem)
                )
                state["sources"] = SourceGroup(source)
                parent.insert(idx, elem)
                self._process_elem(state, elem)
            return

        if state["fetch"]:
            path = self.label.getelementpath(t_elem)
            s_elems = state["sources"].primary.findall(path)
            if len(s_elems) > 1:
                if state["multi"] is not True and len(s_elems) != state["multi"]:
                    raise PTFetchError(
                        f"{len(s_elems)} source elements found but pt:multi is set to"
                        f" expect {int(state['multi'])}",
                        t_elem,
                    )  # cast False to 0 for readability
                self._process_multi_branch(t_elem, parent_state, len(s_elems) - 1)
                return
            elif not len(s_elems):
                if state["required"]:
                    url = state["sources"].primary.docinfo.URL
                    source_file = (
                        Path(url).name if url is not None else "<unresolved filename>"
                    )
                    raise PTFetchError(
                        f"{qname.localname} could not be located at path {path} in"
                        f" source {state.exp['sources']} from {source_file}",  # FIXME: .exp is None in descendants where source is inherited...
                        t_elem,
                    )
                t_elem.getparent().remove(t_elem)
                return
            elif not len(t_elem):  # len(s_elems) == 1:
                t_elem.attrib.update(s_elems[0].attrib)
                t_elem.text = s_elems[0].text
        else:
            if isinstance(state["multi"], int) and state["multi"] > 1:
                self._process_multi_branch(t_elem, parent_state, state["multi"] - 1)
                return
            # non-fetch required condition; should be evaluated at export
            if state.exp["required"] is not None:
                self._deferred_reqs.append(state)

        if len(t_elem):
            for child_elem in t_elem.getchildren():
                self._process_elem(state, child_elem)
        elif state.exp["fill"]:
            if state["defer"]:
                self._deferred_fills.append(state)
            else:
                self._handle_fill(state.t_elem, state.eval_deferred("fill"))

        state.remove_elem_pt_attrs()

    def _process_multi_branch(self, elem, parent_state, num_copies):
        # prevent multi expectation on sibling passes
        del elem.attrib[self._pt_clark("multi")]
        siblings = [deepcopy(elem) for _ in range(num_copies)]
        parent = elem.getparent()
        # insert the siblings after t_elem in document order to keep it tidy
        idx = parent.index(elem) + 1
        for sibling in reversed(siblings):  # reverse to counteract insert order
            parent.insert(idx, sibling)
        # recurse to t_elem also to keep the logic of this branch simple
        pmb = parent_state["multi_branch"]
        for i, elem in enumerate((elem, *siblings)):
            parent_state["multi_branch"] = i
            self._process_elem(parent_state, elem)
        parent_state["multi_branch"] = pmb

    def _eval_deferred_fills(self):
        for state in self._deferred_fills:
            self._ext.set_elem_context(state.t_elem)
            self._handle_fill(state.t_elem, state.eval_deferred("fill"))
        self._deferred_fills = []

    @staticmethod
    def _handle_fill(elem: etree._Element, val: Union[str, list]):
        if not isinstance(val, list):
            val = [val]
        text = elem.text if elem.text is not None else ""
        num_tokens = text.count(FILL_TOKEN)
        if not text or not num_tokens:
            if len(val) == 1:
                # TODO: log weak warning if existing text? e.g.:
                # if len(text.strip()):
                #     print(f"overwriting {text} with {val[0]}")
                text = val[0]
            else:
                _issue = "is empty" if not text else "contains no format tokens"
                raise PTEvalError(
                    f"{PT_NS['prefix']}:fill yielded {len(val)} substitutions but the"
                    f" element's text {_issue}",
                    elem,
                )
        else:
            if num_tokens != len(val):
                _only = " only" if num_tokens < len(val) else ""
                _s = "s" if len(val) > 1 else ""
                raise PTEvalError(
                    f"{PT_NS['prefix']}:fill yielded {len(val)} substitution{_s} but"
                    f" the element's text{_only} contains {num_tokens} format tokens",
                    elem,
                )
            text = elem.text.format(*val)
        elem.text = text

    def _prune_empty_optionals(self):
        # evaluate requireds inside-out to allow nested statements
        # (e.g. for optional class with optional children)
        for state in reversed(self._deferred_reqs):
            self._ext.set_elem_context(state.t_elem)
            required = state.eval_deferred("required")
            if not required:
                pop = empty = False
                # .iter() includes the t_elem itself (for if it's a leaf node)
                for child in state.t_elem.iter("*"):
                    if len(child):
                        continue  # only interested in PDS4 attributes / leaf nodes
                    status = is_populated(child)
                    pop |= status
                    empty |= not status
                    if pop and empty:
                        break  # early loop exit as we know the subtree is dirty
                if empty:
                    parent = state.t_elem.getparent()
                    # t_elem is no longer in the tree (removed after handoff to client)
                    if parent is None:
                        continue
                    if self._label_pre_handoff is not None:
                        # kluge to keep the comparison copy in sync
                        # (else tree comparison will fail later)
                        twin = self._label_pre_handoff.find(
                            self.label.getelementpath(state.t_elem)
                        )
                        # if elem not in label copy then that's fine since we're pruning
                        if twin is not None:
                            twin.getparent().remove(twin)
                    if pop:
                        self._log.warning(
                            f"Pruning partially populated {state.t_elem.tag}"
                        )
                    else:
                        self._log.info(f"Pruning empty {state.t_elem.tag}")
                    parent.remove(state.t_elem)
                # elif pop and empty:
                #     print(
                #         "non-fetch required element contains both populated and"
                #         " unpopulated children"
                #     )
        self._deferred_reqs = []

    def _ensure_populated(self):
        for child in self.root.iter("*"):
            if len(child):
                continue
            if not is_populated(child):
                raise PTTemplateError(
                    f"unpopulated leaf node encountered at export", child
                )

    def _check_structure(self):
        if self._label_pre_handoff is None:
            self._log.info("Skipping structure check")
            return
        added = []
        removed = []
        for a, b, record in (
            (self.label, self._label_pre_handoff, added),
            (self._label_pre_handoff, self.label, removed),
        ):
            for elem in a.getroot().iter("*"):
                path = a.getelementpath(elem)
                if b.find(path) is None:
                    record.append((elem.tag, path))

        if len(added) or len(removed):
            pm = PathManipulator(
                self.nsmap
            )  # FIXME: issue if label nsmaps have gone out of sync; merge?
            msg = [
                "the label structure has been altered after template parsing and"
                " population."
            ]
            for name, record in {"Added": added, "Removed": removed}.items():
                if len(record):
                    msg.append(f"\n{name} elements:")
                    for tag, path in record:
                        msg.append(
                            f"{pm.clark_to_prefix(tag)} @ {pm.clark_to_prefix(path)}"
                        )
            raise PTTemplateError("\n".join(msg))

    @staticmethod
    def _pt_clark(property: str):
        return f"{{{PT_NS['uri']}}}{property}"

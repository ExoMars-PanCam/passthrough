import logging
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional, Sequence, Union
import typing

from lxml import etree

from . import FILL_TOKEN, PT_NS, __project__
from .exc import PTEvalError, PTFetchError, PTTemplateError
from .extensions import ExtensionManager
from .extensions.file import FileHandler
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
            skip_structure_check: If enabled, shave a few milliseconds off the export
                process (and some kilobytes of memory) by not sanity-checking the
                structure of the partial label against that of the original `template`.
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

        # Save the top level source list.
        self._sources = self._source_map_to_etree_map(source_map)

        # Parse the XML template.
        try:
            self.label = labellike_to_etree(template)
        except TypeError as e:
            raise TypeError(f"template is in an {e}") from None

        # Add "template" to our sources list, if requested and
        # safe.
        if template_source_entry:
            if "template" in self._sources:
                raise KeyError(
                    "source map already contains a mapping for the key 'template'"
                )
            self._sources["template"] = self.label

        # Strip comments if requested.
        if not keep_template_comments:
            etree.strip_elements(self.label, etree.Comment, with_tail=False)

        # For convenience, save the template tree root and nsmap.
        self.root = self.label.getroot()
        self.nsmap = add_default_ns(self.root.nsmap)

        self._ext = ExtensionManager()
        self._ext.resources["pt"]["context_map"] = context_map

        self._reorder = []
        self._deferred_fills = []
        self._deferred_reqs = []

        # Recurse down the template tree, filling out what we can.
        self._process_elem(
            PTState(parent=None, t_elem=None, source_map=self._sources), self.root
        )
        self._reorder_children()

        self._label_pre_handoff = None if skip_structure_check else deepcopy(self.label)

        # Ensure sensible t_elem context for ext func eval after handoff
        self._ext.set_elem_context(self.root)

    def export(self, directory: Union[Path, str], filename: str) -> None:
        """Export the partial label to the filesystem.

        Run the partial label through a series of post-processing steps before exporting
        the completed label to `filename` in `directory`.

        In particular, if file handlers have been registered, run them to
        create ancillary files. See, for example, proctools.products.pancam.file_handlers.

        Args:
            directory: Path to the desired output directory.
            filename: Filename override to use for the output label.
        """
        for fh_elem, fh in self._ext.resources["file"]["handlers"].items():
            self._log.debug(f"Writing data file to disk: '{fh.file_name}'")
            fh.write(directory)
        self._eval_deferred_fills()
        self._prune_empty_optionals()
        self._ensure_populated()
        self._check_structure()
        etree.cleanup_namespaces(self.label)
        if not isinstance(directory, Path):
            directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.label.write(
            str(directory / filename),
            encoding="UTF-8",
            pretty_print=True,
            xml_declaration=True,
        )

    def register_file_handler(self, fh: FileHandler) -> None:
        """
        """
        if not isinstance(fh, FileHandler):
            raise TypeError(f"'{type(fh)}' is not a descendant of 'FileHandler'")
        self._ext.resources["file"]["handlers"][fh.t_elem] = fh

    def _source_map_to_etree_map(
        self, smap: Dict[str, Union[LabelLike, Sequence[LabelLike]]]
    ) -> None:
        """
        Iterate over the sources map, reading in all the identified XML
        files and parsing to lxml element trees. We cache items by name
        so that sources which are named more than once don't have to be
        parsed multiple times.
        """

        cache = {}
        for key in smap:
            if key in cache:
                smap[key] = cache[key]
            else:
                try:
                    if isinstance(
                        smap[key], typing.get_args(LabelLike)
                    ):
                        smap[key] = cache[key] = labellike_to_etree(smap[key])
                    else:
                        smap[key] = cache[key] = [
                            labellike_to_etree(ll) for ll in smap[key]
                        ]
                except TypeError as e:
                    raise TypeError(f"source map key {key} maps to an {e}") from None
        return smap

    def _process_elem(self, parent_state: PTState, t_elem: etree._Element) -> None:
        """
        Recursively process elements in the tree from t_elem. Each element
        needs to know its parent's PTState so it can inherit from it as
        necessary. In some cases (multi-*) we'll be patching the parent
        element to add new children (i.e. siblings of the current element)
        and recursing those siblings too.
        """

        if isinstance(t_elem, etree._Comment):
            # Comments don't need further processing.
            return

        self._ext.set_elem_context(t_elem)

        # Make new PT state object for this element, inheriting
        # settings from our parent where appropriate.
        state = PTState(parent_state, t_elem)

        # FIXME: reorder isn't described anywhere.
        if state["reorder"]:
            self._reorder.append(state)

        # If we've got multiple sources, we'll be duplicating this element
        # multiple times as children of its parent.
        if len(state["sources"].secondary) > 0:
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
                # We'll either insert a deep copy of the element, for
                # secondaries, or the element itself for the primary.
                elem = (
                    t_elem if source is state["sources"].primary else deepcopy(t_elem)
                )

                parent.insert(idx, elem)

                # Now make a source group which points only to the
                # primary source and call ourself to process the
                # (possibly newly created) element.
                state["sources"] = SourceGroup(source)
                self._process_elem(state, elem)

            # We don't process any further - the recursion above will
            # have done that.
            return

        if state["fetch"]:
            # We've been asked to fill out this element from a source.

            # Get the current element's path.
            path = self.label.getelementpath(t_elem)

            # Look up this path in the primary source.
            s_elems = state["sources"].primary.findall(path)
            if len(s_elems) > 1:
                # More than one item found at this path? Were we expecting
                # this?
                if state["multi"] is not True and len(s_elems) != state["multi"]:
                    raise PTFetchError(
                        f"{len(s_elems)} source elements found but pt:multi is set to"
                        f" expect {int(state['multi'])}",
                        t_elem,
                    )  # cast False to 0 for readability

                # OK, we were. Process it.
                self._process_multi_branch(t_elem, parent_state, len(s_elems) - 1)
                return
            elif len(s_elems) == 0:
                # Not found in the source. Was it required?
                if state["required"]:
                    # Yes. This is an error. Construct a message.
                    url = state["sources"].primary.docinfo.URL
                    source_file = (
                        Path(url).name if url is not None else "<unresolved filename>"
                    )
                    path = PathManipulator(self.nsmap).clark_to_prefix(path)
                    qname = etree.QName(t_elem.tag)
                    raise PTFetchError(
                        f"{qname.localname} could not be located at path {path} in"
                        f" source {state.exp['sources']} from {source_file}",  # FIXME: .exp is None in descendants where source is inherited...
                        t_elem,
                    )
                # OK, it wasn't required, so we can just remove it from the
                # tree.
                t_elem.getparent().remove(t_elem)
                return
            elif not len(t_elem):  # len(s_elems) == 1:
                # Copy over XML attributes and text from the source.
                t_elem.attrib.update(s_elems[0].attrib)
                t_elem.text = s_elems[0].text
        else:
            # If "multi" attribute is a positive number, call
            # _process_multi_branch, which will duplicate t_elem
            # the specified number of times and recurse into the
            # resulting elements (and the original).
            if isinstance(state["multi"], int) and state["multi"] > 1:
                self._process_multi_branch(t_elem, parent_state, state["multi"] - 1)
                return

            # Non-fetch but required condition; should be evaluated at
            # export to confirm that it's been filled in by the end user
            # code.
            if state.exp["required"] is not None:
                self._deferred_reqs.append(state)

        # etree._Element acts like a list whose members are its child elements.
        if len(t_elem) != 0:
            # Recurse into each child.
            for child_elem in t_elem.getchildren():
                self._process_elem(state, child_elem)
        elif state.exp["fill"]:
            # No children, and fill has been requested.
            if state["defer"]:
                # We've been asked to do the fill at export time. I assume
                # this is so the end user can e.g. place a format string
                # into the element text before final evaluation.
                self._deferred_fills.append(state)
            else:
                # Fill it out now.
                self._handle_fill(state.t_elem, state.eval_deferred("fill"))

        # We're done with this element and its children, so can remove the passthrough
        # attributes we added. Deferred operations can still be identified
        # via the _deferred_fills list.
        state.remove_elem_pt_attrs()

    def _process_multi_branch(self, elem: etree._Element, parent_state: PTState, num_copies: int) -> None:
        """
        This element needs to be duplicated a number of times as children of
        the parent element. Each child is then recursed.
        """
        # Prevent siblings also trying to do multi-passes
        del elem.attrib[self._pt_clark("multi")]

        # We're going to be inserting new elements into the parent...
        parent = elem.getparent()

        # ... after the current element.
        idx = parent.index(elem) + 1

        # FIXME - Why do we reverse? Aren't they identical at this point?
        #
        # Make copies of the current element.
        siblings = [deepcopy(elem) for _ in range(num_copies)]
        for sibling in reversed(siblings):  # reverse to counteract insert order
            parent.insert(idx, sibling)

        # Recurse through the current element *and* its siblings. We keep
        # track of the branch number via the parent state's "multi_branch"
        # value.
        pmb = parent_state["multi_branch"]
        for i, elem in enumerate((elem, *siblings)):
            parent_state["multi_branch"] = i
            self._process_elem(parent_state, elem)
        parent_state["multi_branch"] = pmb

    def _eval_deferred_fills(self) -> None:
        """
        Run through fills marked as deferred, handling them now.
        """
        for state in self._deferred_fills:
            self._ext.set_elem_context(state.t_elem)
            self._handle_fill(state.t_elem, state.eval_deferred("fill"))
        self._deferred_fills = []

    @staticmethod
    def _handle_fill(elem: etree._Element, val: Union[str, list]):
        """
        Modify elem's text using the content in val.

        val can be a string or a list. In the case where it's a string,
        it'll be converted to a list containing one string.

        The template's element text will be used via Python's str.format
        method to format the items in val. If the template's element text
        is purely white space, it will be treated as containing a single
        "{}" token.

        FIXME: This all feels a bit wrong as it stands:
        If we have multiple values and the number of {} tokens in the
            template doesn't match len(values) then we raise an exception.
        If we have multiple values, we replace {} tokens in the
            text with items from the list.
        If we have a single value and the text contains {} then we format as above.
        If we have a single value and the text does not contain {}
            then we *replace* the text without an error.

        Examples:
            elem.text = "",            val=["Goodbye"] => elem.text = "Goodbye"
            elem.text = "Hello world", val=["Goodbye"] => elem.text = "Goodbye"
            elem.text = "Hello {}",    val=["Goodbye"] => elem.text = "Hello Goodbye"
            elem.text = "Hello {} {}", val=["Goodbye"] => Exception
            elem.text = "Hello world", val=["a", "b"]  => Exception

        Seems to me we could instead do:

        if elem.text is None or elem.text.strip() == "":
            text = "{}"
        else:
            text = elem.text

        num_tokens = text.count(FILL_TOKEN)
        if len(val) != num_tokens:
            raise PTEvalError("some meaningful message")
        elem.text = text.format(*val)

        In which case:
            elem.text = "",            val=["Goodbye"] => elem.text = "Goodbye"
            elem.text = "Hello world", val=["Goodbye"] => Exception
            elem.text = "Hello {}",    val=["Goodbye"] => elem.text = "Hello Goodbye"
            elem.text = "Hello {} {}", val=["Goodbye"] => Exception
            elem.text = "Hello world", val=["a", "b"]  => Exception

        This seems more consistent.

        """

        # Make a bare string into a list.
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

    def _reorder_children(self) -> None:
        """
        Elements can be marked with pt:reorder=true(), in which case they'll end
        up in self._reorder.

        Specifying reorder tells passthrough that child elements should
        largely match their order in the source document, rather than the
        template. In cases where the template has added elements, those
        elements should retain their relative ordering *after* the source
        document ordering has been applied.
        """
        for state in self._reorder:
            # Get the template element.
            t_elem = state.t_elem

            # Get the primary source element with the same path as this.
            s_elem = state["sources"].primary.find(self.label.getelementpath(t_elem))

            tags = defaultdict(list)
            order = []

            # Group t_elem's children by tag, preserving relative order
            # within groups.
            for child in t_elem:
                tags[child.tag].append(child)

            # Build a preliminary order for t_elem's children matching that of s_elem's
            # by, for each child of s_elem in order, selecting the t_elem child with
            # the same tag whose instance number is lowest (if one is found).
            for child in s_elem:
                tag = tags[child.tag]
                if len(tag):
                    order.append(tag.pop(0))

            # Ensure that any child only present in t_elem is placed after its
            # preceding sibling from the original template document order. This is not
            # infallible, but should prevent most PDS4 out-of-order errors for added
            # attributes.
            for li in tags.values():
                for child in li:
                    prev_sibling = child.getprevious()
                    order.insert(order.index(prev_sibling) + 1, child)

            # FIXME: This looks very weird. Isn't order exactly the array we
            # need, in which case, can't we just copy across rather than
            # using sorted?

            # Sort t_elem's children in-place using the derived element order
            t_elem[:] = sorted(t_elem, key=lambda e: order.index(e))

    def _prune_empty_optionals(self) -> None:
        """
        Remove elements that are marked as optional when they're empty and
        all optional child elements are also empty.
        """

        # The _deferred_reqs list is filled out as we head down the tree.
        # So iterating it in reversed order means we're working back up
        # the tree. We need this so we can handle nested elements properly
        # (e.g. if we have an optional parent with optional children, we
        # need to know whether any of those children have a value before we
        # can decide whether to prune the parent).
        for state in reversed(self._deferred_reqs):
            self._ext.set_elem_context(state.t_elem)

            # If this element is marked as required then we need to keep it
            # irrespective of its content.
            required = state.eval_deferred("required")
            if not required:
                populated_elements = empty_elements = False

                # Recurse through t_elem and its children.
                for child in state.t_elem.iter("*"):
                    if len(child) != 0:
                        # We're only interested in PDS4 attributes
                        # (i.e. leaf nodes)
                        continue

                    # is_populated returns True if the child has content
                    # or is marked with xsi:nil.
                    status = is_populated(child)

                    # Remember whether any elements were populated and
                    # whether any were empty.
                    populated_elements |= status
                    empty_elements |= not status

                    # If we have both populated and empty elements,
                    # we know enough and can break out of the loop
                    # early.
                    if populated_elements and empty_elements:
                        break

                if empty_elements:
                    parent = state.t_elem.getparent()

                    # Check whether this element is still in the tree - it
                    # may have been removed by client code.
                    if parent is None:
                        continue

                    # If structure checking has been requested then
                    # we need pruning of the "live" copy to be replicated
                    # on the "check" copy, otherwise the subsequent
                    # structure check may fail.
                    if self._label_pre_handoff is not None:
                        twin = self._label_pre_handoff.find(
                            self.label.getelementpath(state.t_elem)
                        )
                        # If the element isn't in the "check" copy, that's
                        # OK, since we're about to remove it anyway.
                        if twin is not None:
                            twin.getparent().remove(twin)

                    # Log what we're up to.
                    if populated_elements:
                        # Why is it OK to prune partially populated trees?
                        # This is covered in the docs - if the template had
                        # e.g. a "description" static element, the tree
                        # containing it could never be pruned in that case.
                        self._log.warning(
                            f"Pruning partially populated {state.t_elem.tag}"
                        )
                    else:
                        self._log.debug(f"Pruning empty {state.t_elem.tag}")

                    # And remove it.
                    parent.remove(state.t_elem)
                # elif populated_elements and empty_elements:
                #     print(
                #         "non-fetch required element contains both populated and"
                #         " unpopulated children"
                #     )
        # Empty the list because we've now handled them all.
        #
        # FIXME: Is this sensible - what if we call export() twice, with
        # further processing in between?
        self._deferred_reqs = []

    def _ensure_populated(self) -> None:
        """
        Check that all leaf elements have content and raise an
        exception if not.
        """

        for child in self.root.iter("*"):
            if len(child) > 0:
                # Not a leaf node.
                continue

            if not is_populated(child):
                raise PTTemplateError(
                    "unpopulated leaf node encountered at export", child
                )

    def _check_structure(self) -> None:
        """
        If structure checking has been requested, do it and raise
        an exception if the check fails.
        """

        # _label_pre_handoff is set when checking has been
        # requested in the constructor.
        if self._label_pre_handoff is None:
            self._log.info("Skipping structure check")
            return

        # Get list of added/removed elements.
        added = []
        removed = []

        # This is a fairly sneaky way of doing two-way checking. I'd
        # probably have done it as two separate loops, and I may well
        # change it to work like that later. FIXME.
        for a, b, record in (
            (self.label, self._label_pre_handoff, added),
            (self._label_pre_handoff, self.label, removed),
        ):
            # Iterate "a" and check whether corresponding elements exist in
            # "b". If not, add the tag/path to "record".
            for elem in a.getroot().iter("*"):
                path = a.getelementpath(elem)
                if b.find(path) is None:
                    record.append((elem.tag, path))

        # Some elements have been added or removed.
        if len(added) > 0 or len(removed) > 0:
            pm = PathManipulator(
                self.nsmap
            )  # FIXME: issue if label nsmaps have gone out of sync; merge?

            # Build our error message.
            msg = [
                "The label structure has been altered after template parsing and"
                " population."
            ]

            # Again, we're using a loop to avoid having two checks. Really
            # not sure I like this approach. FIXME.
            for name, record in {"Added": added, "Removed": removed}.items():
                if len(record) > 0:
                    # Make a list of added/removed elements for the
                    # exception.
                    msg.append(f"\n{name} elements:")
                    for tag, path in record:
                        msg.append(
                            f"{pm.clark_to_prefix(tag)} @ {pm.clark_to_prefix(path)}"
                        )
            # And raise it.
            raise PTTemplateError("\n".join(msg))

    @staticmethod
    def _pt_clark(property: str) -> str:
        """
        Convert a property name to a "clark" qualified name.
        """
        return f"{{{PT_NS['uri']}}}{property}"

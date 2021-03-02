from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional, Sequence, Union

from lxml import etree

from .exc import PTFetchError, PTTemplateError
from . import ext
from . import util
from .state import PTState, SourceGroup


class Template:
    def __init__(self,
                 label: etree._ElementTree,
                 source_map: Dict[str, Union[etree._ElementTree, Sequence[etree._ElementTree]]],
                 context_map: Optional[dict] = None,
                 keep_template_comments: bool = False,
                 skip_structure_check: bool = False):
        self.sources = source_map
        self.label = label
        if not keep_template_comments:
            etree.strip_elements(self.label, etree.Comment, with_tail=False)
        self.root = self.label.getroot()

        self.nsmap = util.add_default_ns(self.root.nsmap)

        self.context_map = ext.Context(context_map)
        builtin_extensions = [
            ext.self,
            ext.vid_increment,
            ext.lid_to_browse_lid,
            ext.datetime_inc,
            self.context_map.context,
        ]
        self.extensions = ext.XPathExtensionManager()
        self.extensions.register(builtin_extensions)

        # self.path_util = PathManipulator(self.root.nsmap, self._default_ns_prefix)
        self._deferred_fills = []
        self._deferred_reqs = []

        # TODO: refactor out into parser/evaluator/pre-processor class?
        self._process_elem(PTState(parent=None, t_elem=None, source_map=self.sources), self.root)

        self._label_pre_handoff = None if skip_structure_check else deepcopy(self.label)

    def export(self, directory: Union[Path, str], filename: Optional[str] = None):
        self._eval_deferred_fills()
        self._prune_empty_optionals()
        self._ensure_populated()
        self._check_structure()
        etree.cleanup_namespaces(self.label)
        if filename is None:
            lid = self.label.xpath("pds:Identification_Area/pds:logical_identifier/text()", namespaces=self.nsmap)[0]
            filename = f"{lid.split(':')[-1]}.xml"  # ExoMars/PSA specific
        if not isinstance(directory, Path):
            directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.label.write(str(directory/filename), encoding="UTF-8", pretty_print=True, xml_declaration=True)

    def _process_elem(self, parent_state: PTState, t_elem: etree._Element):
        if isinstance(t_elem, etree._Comment):
            return
        self.extensions.set_elem_context(t_elem)
        qname = etree.QName(t_elem.tag)
        state = PTState(parent_state, t_elem)

        if len(state["sources"].secondary):  # duplicate subtree for each source
            del t_elem.attrib[util.pt_clark("sources")]  # prevent triggering this processing branch on sibling passes
            # We temporarily detach the t_elem subtree and insert each elem subtree at the original location of t_elem
            # before populating, which ensures that resolved paths are always in the form /path/to/elem[1]/child, which
            # will match corresponding source elements (e.g. /path/to/elem/child) in the multi source fetch scenario.
            # Caveat: downstream deferred pt:fill or pt:required will be evaluated in the context of their element's
            # final path (e.g. /path/to/elem[3]/child).
            # Inserting and populating the subtrees in reverse order ensures that their final document order for multi
            # source fetches is aligned with the order of the source_map sources.
            parent = t_elem.getparent()
            idx = parent.index(t_elem)
            parent.remove(t_elem)
            for source in reversed((state["sources"].primary, *state["sources"].secondary)):
                elem = t_elem if source is state["sources"].primary else deepcopy(t_elem)
                state["sources"] = SourceGroup(source)
                parent.insert(idx, elem)
                self._process_elem(state, elem)
            return

        if state["fetch"]:
            path = self.label.getelementpath(t_elem)
            s_elems = state["sources"].primary.findall(path)
            if len(s_elems) > 1:
                if state["multi"] is not True and len(s_elems) != state["multi"]:
                    raise PTFetchError(f"{len(s_elems)} source elements found but pt:multi is set to expect "
                                       f"{int(state['multi'])}", t_elem)  # cast False to 0 for readability
                self._process_multi_branch(t_elem, parent_state, len(s_elems) - 1)
                return
            elif not len(s_elems):
                if state["required"]:
                    url = state['sources'].primary.docinfo.URL
                    source_file = Path(url).name if url is not None else "<unresolved filename>"
                    raise PTFetchError(f"{qname.localname} could not be located at path {path} in source "
                                       f"{state.exp['sources']} from {source_file}", t_elem)
                # if not state["keep"]:
                t_elem.getparent().remove(t_elem)
                return
            elif not len(t_elem):  # len(s_elems) == 1:
                t_elem.attrib.update(s_elems[0].attrib)
                t_elem.text = s_elems[0].text
        else:
            if isinstance(state["multi"], int) and state["multi"] > 1:
                self._process_multi_branch(t_elem, parent_state, state["multi"])
                return
            if state.exp["required"]:  # non-fetch required condition; should be evaluated at export
                self._deferred_reqs.append(state)

        if len(t_elem):
            for child_elem in t_elem.getchildren():
                self._process_elem(state, child_elem)
        elif state.exp["fill"]:
            if state["defer"]:
                self._deferred_fills.append(state)
            else:
                t_elem.text = state.eval_deferred("fill")

        state.remove_elem_pt_attrs()

    def _process_multi_branch(self, elem, parent_state, num_duplicates):
        del elem.attrib[util.pt_clark("multi")]  # prevent multi expectation on sibling passes
        siblings = [deepcopy(elem) for _ in range(num_duplicates)]
        parent = elem.getparent()
        idx = parent.index(elem) + 1  # insert the siblings after t_elem in document order to keep it tidy
        for sibling in siblings:
            parent.insert(idx, sibling)
        for elem in (elem, *siblings):  # recurse to t_elem also to keep the logic of this branch simple
            self._process_elem(parent_state, elem)

    def _eval_deferred_fills(self):
        for state in self._deferred_fills:
            self.extensions.set_elem_context(state.t_elem)
            state.t_elem.text = state.eval_deferred("fill")
        self._deferred_fills = []

    def _prune_empty_optionals(self):
        for state in self._deferred_reqs:
            self.extensions.set_elem_context(state.t_elem)
            required = state.eval_deferred("required")
            if not required:
                pop = empty = False
                for child in state.t_elem.iter("*"):  # .iter() includes the t_elem itself (for if it's a leaf node)
                    if len(child):
                        continue  # only interested in PDS4 attributes / leaf nodes
                    status = util.is_populated(child)
                    pop |= status
                    empty |= not status
                    if pop and empty:
                        break  # early loop exit as we know the subtree is dirty
                if empty:
                    parent = state.t_elem.getparent()
                    if parent is None:  # t_elem is no longer in the tree (removed after handoff to client)
                        continue
                    if self._label_pre_handoff is not None:
                        # kluge to keep the comparison copy in sync (else tree comparison will fail later)
                        twin = self._label_pre_handoff.find(self.label.getelementpath(state.t_elem))
                        if twin is not None:  # if elem not in label copy then that's fine since we're pruning anyway
                            twin.getparent().remove(twin)
                    if pop:  # TODO: implement proper logging
                        print(f"WARNING: pruning partially populated {state.t_elem.tag}")
                    else:
                        print(f"INFO: pruning empty {state.t_elem.tag}")
                    parent.remove(state.t_elem)
                # elif pop and empty:  # keep for now but warn to provide insight into cause
                #     print("non-fetch required element contains both populated and unpopulated children")
        self._deferred_reqs = []

    def _ensure_populated(self):
        for child in self.root.iter("*"):
            if len(child):
                continue
            if not util.is_populated(child):
                raise PTTemplateError(f"unpopulated leaf node encountered at export", child)

    def _check_structure(self):
        if self._label_pre_handoff is None:
            # TODO: log that structure check has been skipped
            print("INFO: skipping structure check")
            return
        added = []
        removed = []
        for a, b, record in ((self.label, self._label_pre_handoff, added),
                             (self._label_pre_handoff, self.label, removed)):
            for elem in a.getroot().iter("*"):
                path = a.getelementpath(elem)
                # print(f"{path} -- {b.find(path)}")
                if b.find(path) is None:
                    record.append((elem.tag, path))

        if len(added) or len(removed):
            pm = util.PathManipulator(self.nsmap)  # FIXME: issue if label nsmaps have gone out of sync; merge?
            msg = ["the label structure has been altered after template parsing and population."]
            for name, record in {"Added": added, "Removed": removed}.items():
                if len(record):
                    msg.append(f"\n{name} elements:")
                    for tag, path in record:
                        msg.append(f"{pm.clark_to_prefix(tag)} @ {pm.clark_to_prefix(path)}")
            raise PTTemplateError("\n".join(msg))

from collections import OrderedDict, UserDict, namedtuple
from typing import Dict, Optional, Sequence, Union

from lxml import etree

from . import PT_NS
from .exc import PTEvalError, PTStateError, PTSyntaxError, PTTemplateError
from .label_tools import add_default_ns

Property = namedtuple("Property", ("default", "inherit", "types"))


class SourceGroup:
    def __init__(
        self, members: Optional[Union[etree._ElementTree, Sequence[etree._ElementTree]]]
    ):
        if isinstance(members, etree._ElementTree) or members is None:
            self.primary = members
            self.secondary = ()
        elif not len(members):
            raise ValueError("group is empty")
        elif len(set(members)) < len(members):
            raise ValueError("group contains duplicate ElementTrees")
        elif False in [isinstance(member, etree._ElementTree) for member in members]:
            raise TypeError("group contains a non-ElementTree member")
        else:
            self.primary = members[0]
            self.secondary = members[1:]  # safe because even [True][1:] => []


class PTState(UserDict):
    _PROPERTIES = OrderedDict(
        [
            (
                "sources",
                Property(default=SourceGroup(None), inherit=True, types=(None,)),
            ),
            ("fetch", Property(default=False, inherit=True, types=(bool,))),
            ("multi", Property(default=False, inherit=False, types=(bool, int))),
            ("required", Property(default=True, inherit=True, types=(bool,))),
            ("fill", Property(default=None, inherit=False, types=(str,))),
            ("defer", Property(default=False, inherit=False, types=(bool,))),
            ("multi_branch", Property(default=None, inherit=True, types=(int,))),
            ("reorder", Property(default=False, inherit=False, types=(bool,))),
        ]
    )

    def __init__(
        self,
        parent: "PTState" = None,
        t_elem: etree._Element = None,
        source_map: Dict[
            str, Union[etree._ElementTree, Sequence[etree._ElementTree]]
        ] = None,
    ):
        super().__init__()

        if parent is None and source_map is None:
            ValueError("Both source_map parameter must be provided if parent is not")

        self.t_elem = t_elem
        self._source_map = (
            self._conform_source_map(source_map) if source_map is not None else None
        )
        self.nsmap = None  # (re)set when evaluating the source_map
        self.exp = {kw: None for kw in self._PROPERTIES}
        self.update({kw: prop.default for kw, prop in self._PROPERTIES.items()})

        if parent is not None:
            self._source_map = parent._source_map
            self.nsmap = parent.nsmap
            for kw, prop in self._PROPERTIES.items():
                if prop.inherit:
                    self[kw] = parent.data[kw]

        if self.t_elem is not None:
            self._eval_state()

        if None not in (parent, self.t_elem):
            self._validate_state(parent)

    def eval_deferred(self, prop: str) -> Union[str, list]:
        self._eval_prop(prop, deferred=True)
        return self[prop]

    def remove_elem_pt_attrs(self):
        kws = list(self._PROPERTIES)
        for attr in [f"{{{PT_NS['uri']}}}{kw}" for kw in kws]:
            if attr in self.t_elem.attrib:
                del self.t_elem.attrib[attr]

    @staticmethod
    def _conform_source_map(smap):
        for kw in smap.keys():
            try:
                smap[kw] = SourceGroup(smap[kw])
            except (ValueError, TypeError) as e:
                raise e.__class__(
                    f"error encountered in source group {kw}: {e}"
                ) from None
        return smap

    def _eval_state(self):
        updated = self._extract_exps()
        if len(updated) and "sources" not in updated and not self["sources"].primary:
            raise PTEvalError("No source has been set!", self.t_elem)
        # below loop relies on order of self._PROPERTIES keys, so reorder:
        updated = [k for k in self._PROPERTIES if k in updated]
        for prop in updated:
            if self.exp[prop] is not None:
                self._eval_prop(prop)

    def _eval_prop(self, kw, deferred=False):
        if kw == "sources":
            self["sources"] = self._source_map.get(self.exp["sources"], None)
            if self["sources"] is None:
                raise PTEvalError(
                    f"{self._exp_str('sources')} did not match any source (group)",
                    self.t_elem,
                )
            self.nsmap = add_default_ns(self["sources"].primary.getroot().nsmap)
            return
        elif kw == "fill" and not deferred:
            return
        elif kw == "required" and not self["fetch"] and not deferred:
            self["required"] = None
            return
        try:
            val = self["sources"].primary.xpath(self.exp[kw], namespaces=self.nsmap)
        except etree.XPathError as e:
            raise PTEvalError(
                f"{self._exp_str(kw)} resulted in {e.__class__.__name__}: {e}",
                self.t_elem,
            ) from None  # e
        self[kw] = self._conform_xpath_result(kw, val)

    def _conform_xpath_result(self, kw, val):
        if isinstance(val, self._PROPERTIES[kw].types):
            return val
        if isinstance(val, list):
            if len(val) == 1:
                # try unwrapping the result (e.g. result of './text()')
                return self._conform_xpath_result(kw, val[0])
            if not len(val):
                raise PTEvalError(
                    f"{self._exp_str(kw)} evaluation yielded an empty node-set",
                    self.t_elem,
                )
            if kw != "fill":
                raise PTEvalError(
                    f"{self._exp_str(kw)} evaluation yielded multiple results: {val}",
                    self.t_elem,
                )
            if self["multi_branch"] is not None:
                return self._conform_xpath_result(kw, val[self["multi_branch"]])
            return [self._conform_xpath_result(kw, v) for v in val]
        # XPath returns ints as floats;
        if int in self._PROPERTIES[kw].types and isinstance(val, float):
            val = int(val)
            # v FIXME: why is this guard here? No use cases for negatives?
            if val < 0:
                raise PTEvalError(
                    f"{self._exp_str(kw)} evaluation yielded a negative number: {val}",
                    self.t_elem,
                )
            return val

        if str in self._PROPERTIES[kw].types:
            if isinstance(val, etree._Element):
                # v FIXME: check if .text is None, return "" instead of ending up with
                #    "None"?
                return str(val.text)
            elif isinstance(val, bool):
                # PDS-ify booleans ('True' -> 'true')
                return str(val).lower()
            elif isinstance(val, float):
                return str(val)

        raise PTEvalError(
            f"{self._exp_str(kw)} yielded '{val}' of type {type(val)}, which cannot be"
            f" safely cast to {self._PROPERTIES[kw].types}",
            self.t_elem,
        )

    def _extract_exps(self):
        updated = []
        for attr, exp in self.t_elem.items():
            qname = etree.QName(attr)
            if qname.namespace != PT_NS["uri"]:
                continue
            if qname.localname not in PTState._PROPERTIES:
                raise PTSyntaxError(
                    f"unrecognised PT attribute: {qname.localname}", self.t_elem
                )
            self.exp[qname.localname] = exp
            if not len(exp):
                raise PTEvalError(
                    f"{self._exp_str(qname.localname)} - PT attribute expression is"
                    " empty",
                    self.t_elem,
                )
            updated.append(qname.localname)
        return updated

    def _exp_str(self, param_name: str):
        return f"{PT_NS['prefix']}:{param_name}=\"{self.exp[param_name]}\""

    def _validate_state(self, parent):
        # v FIXME: should also check after deferred eval of required?
        if self["required"] and not parent["required"]:
            raise PTStateError(
                "declaring a child of an unrequired element as required is nonsensical",
                self.t_elem,
            )
        if self["defer"] and self.exp["fill"] is None:
            raise PTStateError(
                "pt:defer is only valid when pt:fill is defined", self.t_elem
            )
        if self.exp["fill"] and len(self.t_elem):
            raise PTStateError("pt:fill defined on a PDS4 class", self.t_elem)
        if not self["fetch"]:
            # TODO: evaluate if there are any use cases that argue against this
            if self["reorder"] is True:
                raise PTStateError(
                    f'pt:reorder="true()" outside a pt:fetch context is not allowed'
                )
            if self["multi"] is True:
                raise PTStateError(
                    f'pt:multi="true()" outside a pt:fetch context is nonsensical',
                    self.t_elem,
                )
            elif self["multi"] is not False and len(self["sources"].secondary):
                raise PTStateError(
                    f"Cannot combine pt:multi ({self['multi']}) and multiple sources"
                    " when pt:fetch is not active",
                    self.t_elem,
                )
        # FIXME: doesn't catch stub classes containing comment(s) if keep_comments==True
        qname = etree.QName(self.t_elem)
        # v leaf node but tag is not a valid PDS4 attribute
        if not len(self.t_elem) and qname.localname[0].isupper():
            raise PTTemplateError("PDS4 class is a stub", self.t_elem)

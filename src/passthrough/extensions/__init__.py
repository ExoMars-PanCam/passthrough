from functools import partial
from typing import Any, MutableMapping, Optional

from lxml import etree

from .. import PT_EXT_URI_BASE, importlib_metadata
from ..label_tools import add_default_ns


def get_extensions():  # -> MutableMapping[str, ModuleType]:
    """ Return a dict of all installed extension modules as {prefix: module}. """
    extensions = importlib_metadata.entry_points(group="passthrough.extensions")
    # FIXME: kluge. Passthrough doesn't register its entry points if installed in dev
    #  mode in another project (e.g. with poetry and develop=true)
    if not len(extensions):
        from . import exm, file, pt

        extensions = {"pt": pt, "exm": exm, "file": file}
    else:
        extensions = {extension.name: extension.load() for extension in extensions}
    return extensions


class ExtensionManager:
    def __init__(self):
        self.t_elem: Optional[etree._Element] = None
        self.function_namespaces: MutableMapping[str, etree.FunctionNamespace] = {}

        extensions = get_extensions()
        for prefix, mod in extensions.items():
            if not hasattr(mod, "functions"):
                raise AttributeError(
                    f"'{prefix}' extension has no attribute 'functions'"
                )
            elif not isinstance(mod.functions, MutableMapping):
                raise TypeError(f"'{prefix}.functions' must be a mapping")
            uri = f"{PT_EXT_URI_BASE}/{prefix}"
            fns = etree.FunctionNamespace(uri)
            fns.prefix = prefix
            for func_name, func in mod.functions.items():
                fns[func_name] = partial(self._dispatch, func)
            self.function_namespaces[prefix] = fns

    def set_elem_context(self, t_elem):
        # during tree traversal: set self.t_elem that will be passed to extensions
        self.t_elem = t_elem

    def _dispatch(self, func, ctx, *args, **kwargs):
        return func(PTContext(self.t_elem, ctx), *args, **kwargs)


class PTContext:
    def __init__(self, t_elem: etree._Element, ctx):
        self._t_elem = t_elem
        self._s_root = ctx.context_node
        self._s_xpath = None
        self._s_nsmap = None
        self._t_root = None
        self._t_xpath = None
        self._t_nsmap = None

    @property
    def t_elem(self) -> etree._Element:
        return self._t_elem

    @property
    def t_root(self) -> etree._Element:
        return self.t_elem.getroottree().getroot()

    @property
    def t_nsmap(self) -> MutableMapping[str, str]:
        if self._t_nsmap is None:
            self._t_nsmap = add_default_ns(self.t_root.nsmap)
        return self._t_nsmap

    def t_xpath(self, expression: str) -> Any:
        if self._t_xpath is None:
            self._t_xpath = etree.XPathEvaluator(self.t_root, namespaces=self.t_nsmap)
        return self._t_xpath(expression)

    @property
    def s_root(self) -> etree._Element:
        return self._s_root

    def s_xpath(self, expression: str) -> Any:
        if self._s_xpath is None:
            self._s_xpath = etree.XPathEvaluator(self.s_root, namespaces=self.s_nsmap)
        return self._s_xpath(expression)

    @property
    def s_nsmap(self) -> MutableMapping[str, str]:
        if self._s_nsmap is None:
            self._s_nsmap = add_default_ns(self.s_root.nsmap)
        return self._s_nsmap

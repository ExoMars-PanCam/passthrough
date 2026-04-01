from copy import deepcopy
from functools import partial
from typing import Any, MutableMapping, Optional

from lxml import etree

from .. import PT_EXT_URI_BASE, importlib_metadata
from ..label_tools import add_default_ns


def get_extensions():  # -> MutableMapping[str, ModuleType]:
    """
    Return a dict of all installed extension modules as {prefix: module}.
    """

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
    """
    ExtensionManager adds a collection of functions to the lxml parser, such
    that they can be used from within templates. Each extension exists as a
    module in the directory below this one. The module should define a
    functions dict which associates names with a module functions. The name
    will be available in the template for pt:* attributes. The most useful
    example of this would be in the use of a pt:fill.

    Example:
        <sometag pt:fill="pt:datetime.now()">TO_BE_FILLED_IN</sometag>

    Each module function will be handed a PTContext object, which holds
    useful context information, such as the current template XML element,
    as its first argument. Other arguments will be supplied from the function
    call in the XML. For example, the datetime.now() call above supplies no
    arguments, so the pt.datetime_now function which backs this call will
    receive a single argument, the PTContext object.
    """
    def __init__(self):
        self.t_elem: Optional[etree._Element] = None

        # FIXME - what is this for? It's only ever written to.
        self.function_namespaces: MutableMapping[str, etree.FunctionNamespace] = {}
        self.resources: MutableMapping[str, MutableMapping[str, Any]] = {}

        extensions = get_extensions()

        # Each extension module declares a prefix, which turns into a namespace
        # (e.g. "pt" as above).
        for prefix, mod in extensions.items():
            # Each extension module declares a "functions" map,
            # which relates names to actual functions. For example,
            # the "pt" extension's "functions" map has an item,
            # "datetime.now": datetime_now.
            if not hasattr(mod, "functions"):
                raise AttributeError(
                    f"'{prefix}' extension has no attribute 'functions'"
                )
            elif not isinstance(mod.functions, MutableMapping):
                raise TypeError(f"'{prefix}.functions' must be a mapping")
            if hasattr(mod, "resources"):
                if not isinstance(mod.resources, MutableMapping):
                    raise TypeError(f"'{prefix}.resources' must be a mapping")
                self.resources[prefix] = deepcopy(mod.resources)
            else:
                self.resources[prefix] = {}
            uri = f"{PT_EXT_URI_BASE}/{prefix}"
            fns = etree.FunctionNamespace(uri)
            fns.prefix = prefix

            for func_name, func in mod.functions.items():
                fns[func_name] = partial(self._dispatch, func, self.resources[prefix])
            self.function_namespaces[prefix] = fns

    def set_elem_context(self, t_elem):
        """
        During tree traversal, the extension manager will be handed the
        current template element. It stores this away for use by
        extension functions, via the _dispatch below.
        """
        self.t_elem = t_elem

    def _dispatch(self, func, resources, lxml_ctx, *args, **kwargs):
        """
        This method wraps an extension function, providing it with the
        extra "context" argument. lxml_ctx is the XPath context, as supplied
        by lxml.
        """
        return func(PTContext(self.t_elem, resources, lxml_ctx), *args, **kwargs)


class PTContext:
    """
    A simple class to pass on useful information to extension functions.
    """
    def __init__(self, t_elem: etree._Element, resources: MutableMapping, lxml_ctx):
        self.resources = resources
        self._t_elem = t_elem
        self._s_root = lxml_ctx.context_node
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

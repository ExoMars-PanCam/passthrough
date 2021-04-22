from functools import partial
from typing import MutableMapping, Optional

from lxml import etree

from .. import PT_EXT_URI_BASE, importlib_metadata


def get_extensions():  # -> MutableMapping[str, ModuleType]:
    """ Return a dict of all installed extension modules as {prefix: module}. """
    extensions = importlib_metadata.entry_points(group="passthrough.extensions")
    return {extension.name: extension.load() for extension in extensions}


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

    def _dispatch(self, func, *args, **kwargs):
        return func(self.t_elem, *args, **kwargs)

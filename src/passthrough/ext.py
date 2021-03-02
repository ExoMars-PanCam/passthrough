from collections import UserDict
from functools import partial
from typing import Callable, Union, Sequence, Mapping

from lxml import etree

from . import util, PT_NS
from .exc import PTEvalError


class XPathExtensionManager:
    def __init__(self):
        self.extensions = {}
        self.t_elem = None
        self.fns = etree.FunctionNamespace(PT_NS["uri"])
        self.fns.prefix = PT_NS["prefix"]

    def set_elem_context(self, t_elem):
        self.t_elem = t_elem
        # during tree traversal: set self.t_elem that will be passed to extension functions

    def register(self, ext: Union[Callable, Sequence[Callable], Mapping[str, Callable]], name: str = None):
        if isinstance(ext, Sequence):
            ext = {extension.__name__: extension for extension in ext}
        elif not isinstance(ext, Mapping):  # single callable
            ext = {name or ext.__name__: ext}

        for name, extension in ext.items():
            self.extensions[name] = extension
            self.fns[name] = partial(self._dispatch, name)  # don't partial extension w/ fixed self.t_elem as it's dynamic

    def _dispatch(self, name, *args, **kwargs):
        return self.extensions[name](self.t_elem, *args, **kwargs)


# Default/builtin extensions

def self(t_elem, _):
    return t_elem


def vid_increment(t_elem, _):
    vid = util.VID(from_string=t_elem.text)
    vid.increment("minor")
    return str(vid)


def lid_to_browse_lid(_, __, lid_string: str):
    lid = util.ProductLIDFormatter(lid_string)
    parts = lid.fields["collection_id"].split("_")
    if len(parts) != 2:
        # Only allow data_* source collections for now (cal collection support TBC)
        raise ValueError(f"Illegal source lid collection encountered: "
                         f"{lid.fields['collection_id']}")
    lid.fields["collection_id"] = "_".join(["browse", parts[-1]])
    return str(lid)


def datetime_inc(_, __, timestamp, delta):
    time = util.ExoMarsDatetime(timestamp[0].text, format_="label")
    time.add_delta(delta[0].text, unit=delta[0].attrib["unit"])
    return str(time)


class Context(UserDict):
    def context(self, t_elem, _, key):
        try:
            return str(self[key])
        except KeyError:
            raise PTEvalError(f"context entry {key} has not been registered", t_elem)

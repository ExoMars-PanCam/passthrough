"""Passthrough - PDS4 label template system

"""
import importlib.metadata as importlib_metadata # type: ignore
_dist_meta = importlib_metadata.metadata("passthrough")
__author__ = _dist_meta["Author"]
__description__ = _dist_meta["Summary"]
__project__ = _dist_meta["Name"]
__url__ = _dist_meta["Home-Page"]
__version__ = _dist_meta["Version"]
del _dist_meta

print(__project__)
PT_NS = {"prefix": "pt", "uri": __url__}
PT_EXT_URI_BASE = f"{__url__}/extensions"
FILL_TOKEN = "{}"

from . import exc, extensions, label_tools
from .template import Template

__all__ = [
    "__author__",
    "__version__",
    "exc",
    "extensions",
    "label_tools",
    "PT_NS",
    "PT_EXT_URI_BASE",
    "Template",
]

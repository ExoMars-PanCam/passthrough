"""Passthrough - PDS4 label template system

"""
try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata
_dist_meta = importlib_metadata.metadata("passthrough")
__author__ = _dist_meta["Author"]
__description__ = _dist_meta["Summary"]
__project__ = _dist_meta["Name"]
__url__ = _dist_meta["Home-Page"]
__version__ = _dist_meta["Version"]
del _dist_meta

PT_NS = {"prefix": "pt", "uri": __url__}

from . import exc, label
from .template import Template

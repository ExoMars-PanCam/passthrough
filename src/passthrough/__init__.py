"""Passthrough - PDS4 label template system

"""
from ._pkg_info import __version__, __author__, __homepage__

PT_NS = {"prefix": "pt", "uri": __homepage__}
DEFAULT_NS_PREFIX = "pds"

from .template import Template
from . import exc

# from . import logger

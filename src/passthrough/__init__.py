"""Passthrough - PDS4 label template system

"""
from ._pkg_info import __author__, __homepage__, __version__

PT_NS = {"prefix": "pt", "uri": __homepage__}

from . import exc, label
from .template import Template

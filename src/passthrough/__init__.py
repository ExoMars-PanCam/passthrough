"""Passthrough - PDS4 label template system

"""

# Bring in some metadata from the package.
import importlib.metadata # type: ignore

# Copy it into module-level variables.
_dist_meta = importlib.metadata.metadata("passthrough")
__author__ = _dist_meta["Author-email"]
__description__ = _dist_meta["Summary"]
__project__ = _dist_meta["Name"]
__version__ = _dist_meta["Version"]

# __url__ is used to create a namespace within the XML data. We need
# something that identifies passthrough uniquely, and the original code
# used the metadata's "repository" value. This is more complicated in
# modern versions of pyproject.toml because URLs are now collapsed into
# a list, possibly with multiple entries.
__url__ = next(
    item.replace("Repository, ", "", 1)
        for item in _dist_meta.get_all("Project-URL")
            if item.startswith("Repository, ")
)
del _dist_meta

# The namespace for use within XML attributes for the main code.
PT_NS = {"prefix": "pt", "uri": __url__}

# Ditto for extensions.
PT_EXT_URI_BASE = f"{__url__}/extensions"

FILL_TOKEN = "{}"

from . import exc, extensions, label_tools
from .template import Template

# This is the list of symbols that will be exported if someone
# does "from passthrough import *"
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

"""PDS4 label interrogation and manipulation functionality"""

__all__ = [
    "LabelLike",
    "PDS_NS_PREFIX",
    "ATTR_PATHS",
    "labellike_to_etree",
    "add_default_ns",
    "is_populated",
    "PathManipulator",
]

from pathlib import Path
from typing import Dict, Optional, Union

from lxml import etree

# pds4_tools is an optional dependency. Try the import and
# handle failure appropriately.
try:
    from pds4_tools.reader.general_objects import StructureList
    from pds4_tools.reader.label_objects import Label
    LabelLike = Union[etree._ElementTree, StructureList, Label, Path, str]
except ModuleNotFoundError:
    StructureList = None
    Label = None

if None not in (StructureList, Label):
    LabelLike = Union[etree._ElementTree, StructureList, Label, Path, str]
else:
    LabelLike = Union[etree._ElementTree, Path, str]

PDS_NS_PREFIX = "pds"

# Common PDS4 attribute XPath shorthands
ATTR_PATHS = {
    "lid": "//pds:Identification_Area/pds:logical_identifier",
    "start": "//pds:Time_Coordinates/pds:start_date_time",
    "stop": "//pds:Time_Coordinates/pds:stop_date_time",
    # "type": "//msn:Mission_Information/msn:product_type_name",
    # "sub_instrument": "//psa:Sub-Instrument/psa:identifier",
    # "exposure_duration": "//img:Exposure/img:exposure_duration",
}


def labellike_to_etree(labellike: LabelLike) -> etree._ElementTree:
    """
    Given a LabelLike object, convert it to an XML
    element tree by parsing a file, structure list or label.

    :param labellike: A LabelLike object.
    :return: lxml element tree.
    """

    # Already an element tree - just return.
    if isinstance(labellike, etree._ElementTree):
        return labellike

    # A path object - expand ~ like the shell does, then resolve
    # any symlinks, then continue to normal str handling.
    if isinstance(labellike, Path):
        labellike = str(labellike.expanduser().resolve())

    # Treat string as a filename and parse it as XML.
    if isinstance(labellike, str):
        return etree.parse(labellike)

    base_url = None

    # A PDS4 structure list, resulting from pds4_tools.read(). Look at
    # the read log to find the name of the XML file, and extract the
    # Label object from the list. Then fall through to the lable handler.
    if StructureList is not None and isinstance(labellike, StructureList):
        prefix = "Processing label: "
        log = labellike.read_in_log.split("\n")[0]
        if log.startswith(prefix):
            # *should* always resolve to the abs path of the XML label
            base_url = log[len(prefix) :]
        labellike = labellike.label

    # A PDS4 label. Convert to string, then parse as XML and get the
    # XML tree from it.
    if Label is not None and isinstance(labellike, Label):
        return etree.fromstring(
            labellike.to_string(unmodified=True), base_url=base_url
        ).getroottree()

    # No matching type.
    raise TypeError(
        f"unknown label format {type(labellike)}, expected one of {LabelLike}"
    )


def add_default_ns(nsmap: Dict[Optional[str], str]) -> Dict[str, str]:
    """
    The default namespace comes from xmlns="...", and ends up stored with
    the key "None" in the _ElementTree object's nsmap. Move this to
    PDS_NS_PREFIX instead.

    :param nsmap: A namespace map with a "None" key.
    :return: Modified map with the "None" key replaced by the default PDS prefix.
    """
    if None in nsmap:
        nsmap[PDS_NS_PREFIX] = nsmap[None]
        del nsmap[None]
    return nsmap


def is_populated(elem: etree._Element) -> bool:
    """
    Check whether an element is populated.
    Handles xsi:nil="true" as populated.

    :param elem: Element
    :return: Boolean indicating whether the element is populated
    """

    # Basic check
    if elem.text is not None and bool(elem.text.strip()):
        return True

    # Element content is empty, but an element should be treated
    # as not empty if it has xsi:nil="true".
    if (
        "xsi" in elem.nsmap
        and elem.attrib.get(f"{{{elem.nsmap['xsi']}}}nil", False) == "true"
    ):
        return True

    # OK, it's properly empty.
    return False


class PathManipulator:
    """
    Utility class for making changes to paths based on namespace data.
    """

    def __init__(self, nsmap: dict, default_prefix: str = PDS_NS_PREFIX):
        self._nsmap = nsmap
        self._default_prefix = default_prefix

    def clark_to_prefix(self, path: str) -> str:
        """
        Transforms paths provided in Clark notation (`{nsURI}tag`) to XPath-valid prefix
        notation (`nsPrefix:tag`).

        :param path: path string in Clark notation (e.g. ElementPath).
        :return: path string in prefix notation.
        """
        for prefix, uri in self._nsmap.items():
            path = path.replace(f"{{{uri}}}", f"{prefix}:")
        return path

    def prefix_default_ns(self, path: str) -> str:
        """
        Transforms a path by prefixing non-empty components
        with the default namespace.

        :param path: path string.
        :return: modified path string.
        """

        segments = []
        for segment in path.split("/"):
            if segment.startswith("*"):
                raise RuntimeError(f"path segment not yet supported: '{segment}'")
            elif ":" in segment:  # assume : marks the end of a prefix in this segment
                segments.append(segment)
            elif len(segment):  # empty segments occur for abs. paths or //
                segments.append(f"{self._default_prefix}:{segment}")
            segments.append("/")
        else:
            segments.pop()  # remove trailing /
        return "".join(segments)

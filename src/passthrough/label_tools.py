"""PDS4 label interrogation and manipulation functionality"""

__all__ = [
    "LabelLike",
    "PDS_NS_PREFIX",
    "ATTR_PATHS",
    "labellike_to_etree",
    "add_default_ns",
    "is_populated",
]

from pathlib import Path
from typing import Dict, Optional, Union

from lxml import etree

try:
    from pds4_tools.reader.general_objects import StructureList
    from pds4_tools.reader.label_objects import Label
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
    if isinstance(labellike, etree._ElementTree):
        return labellike
    if isinstance(labellike, Path):
        labellike = str(labellike.expanduser().resolve())
        # continue to handling of str
    if isinstance(labellike, str):
        return etree.parse(labellike)
    base_url = None
    if StructureList is not None and isinstance(labellike, StructureList):
        prefix = "Processing label: "
        log = labellike.read_in_log.split("\n")[0]
        if log.startswith(prefix):
            # *should* always resolve to the abs path of the XML label
            base_url = log[len(prefix) :]
        labellike = labellike.label
        # continue to handling of Label
    if Label is not None and isinstance(labellike, Label):
        return etree.fromstring(
            labellike.to_string(unmodified=True), base_url=base_url
        ).getroottree()
    raise TypeError(
        f"unknown label format {type(labellike)}, expected one of {LabelLike}"
    )


def add_default_ns(nsmap: Dict[Optional[str], str]) -> Dict[str, str]:
    nsmap[PDS_NS_PREFIX] = nsmap[None]
    del nsmap[None]
    return nsmap


def is_populated(elem: etree._Element):
    if elem.text is not None and bool(elem.text.strip()):
        return True
    if (
        "xsi" in elem.nsmap
        and elem.attrib.get(f"{{{elem.nsmap['xsi']}}}nil", False) == "true"
    ):
        return True
    return False

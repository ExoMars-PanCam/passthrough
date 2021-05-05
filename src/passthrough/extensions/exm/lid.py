from collections import OrderedDict
from copy import deepcopy
from typing import List, Union

from lxml import etree

from ...exc import PTEvalError
from ...label_tools import ATTR_PATHS
from ..pt.datetime import PDSDatetime
from ..pt.vid import VID
from . import ATTR_PATHS_EXM

LID_DATETIME_FORMAT = "%Y%m%dt%H%M%S.%fz"


class ProductLIDFormatter:
    LID_STRUCTURE = OrderedDict(
        {
            "prefix": None,
            "bundle_id": None,
            "collection_id": None,
            "product_id": {
                "instrument": None,
                "processing_level": None,
                "type": None,
                "subunit": None,
                "descriptor": None,
                "time": None,
            },
        }
    )

    def __init__(self, from_string: str = None):
        self.fields = deepcopy(self.LID_STRUCTURE)
        self.vid = None
        if from_string is not None:
            self.from_string(from_string.strip())

    def from_string(self, lid: str):
        fields = lid.split("::")
        if len(fields) == 2:
            self.vid = VID(fields[-1])
            lid = fields[0]
        elif len(fields) > 2:
            raise ValueError(f"Invalid LID: {lid}")

        self._parse_fields(lid)

    def _parse_fields(self, lid: str):
        fields = lid.split(":")
        if len(fields) != 6:
            raise ValueError(f"Invalid number of LID fields ({len(fields)}): {lid}")

        self.fields["prefix"] = ":".join(fields[:3])  # urn:esa:psa
        self.fields["bundle_id"] = fields[3]
        self.fields["collection_id"] = fields[4]

        subfields = fields[5].split("_")
        # <instrument>_<processing_level>_<type>[_<subunit>]_<descriptor>_[<time1>[_<time2>]]
        if len(subfields) not in (5, 6, 7):
            raise ValueError(
                f"Invalid number of subfields ({len(subfields)}): {fields[5]}"
            )

        pid = self.fields["product_id"]
        pid["instrument"] = subfields.pop(0)
        pid["processing_level"] = subfields.pop(0)
        pid["type"] = subfields.pop(0)

        # check for time component(s)
        try:
            time = PDSDatetime(subfields[-1], LID_DATETIME_FORMAT)
        except ValueError:
            # Future: could implement support for e.g. Sol number if required
            # For now, assume product ID only consists of basename
            # TODO: verify valid assumption for EXM/PanCam (i.e. sol number not used)
            pass
        else:
            subfields.pop()
            pid["time"] = [time]
            try:  # I don't like this nesting either...
                time = PDSDatetime(subfields[-2], LID_DATETIME_FORMAT)
            except ValueError:  # no stop_date_time component
                pass
            else:
                subfields.pop()
                pid["time"].insert(0, time)

        pid["descriptor"] = subfields.pop()

        if len(subfields):
            pid["subunit"] = subfields.pop()

    def __str__(self):
        """
        NOTE: currently relies on
        :return:
        """
        if not (
            None not in self.fields.values()
            and None not in self.fields["product_id"].values()
        ):
            raise ValueError("LID is incomplete")  # FIXME: warn instead?
        field_list = []
        for k in self.fields:
            if k == "product_id":
                subfield_list = []
                for kk in self.fields[k]:
                    if kk == "time":
                        time = "_".join([str(e) for e in self.fields[k][kk]])
                        subfield_list.append(time)
                    else:
                        subfield_list.append(self.fields[k][kk])
                field_list.append("_".join(subfield_list))
            else:
                field_list.append(self.fields[k])
        return ":".join(field_list)


def lid_to_browse(_, lid_string: Union[str, List[etree._Element]]):
    if not isinstance(lid_string, str):
        lid_string = lid_string[0].text  # TODO: complain if len > 1 or type not _Elem
    lid = ProductLIDFormatter(lid_string)
    parts = lid.fields["collection_id"].split("_")
    lid.fields["collection_id"] = "_".join(["browse", *parts[1:]])
    return str(lid)


def lid_subunit(ctx):
    type_ = ctx.t_xpath(ATTR_PATHS_EXM["type"])[0].text
    if type_ == "spec-rad":
        pp_200b_lid = ctx.s_xpath(ATTR_PATHS["lid"])[0].text
        subunit = ProductLIDFormatter(pp_200b_lid).fields["product_id"]["subunit"]
    else:
        raise PTEvalError(f"unrecognised product type '{type_}'", ctx.t_elem)
    return subunit


def lid_time(ctx):
    type_ = ctx.t_xpath(ATTR_PATHS_EXM["type"])[0].text
    if type_ == "spec-rad":
        pp_200b_lid = ctx.s_xpath(ATTR_PATHS["lid"])[0].text
        time = str(ProductLIDFormatter(pp_200b_lid).fields["product_id"]["time"][0])
    else:
        raise PTEvalError(f"unrecognised product type '{type_}'", ctx.t_elem)
    return time

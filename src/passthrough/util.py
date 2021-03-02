from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Union, Dict

from lxml import etree

from . import DEFAULT_NS_PREFIX, PT_NS


class ExoMarsDatetime:
    LID_FORMAT = "%Y%m%dt%H%M%S.%fz"
    LABEL_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    _EXPONENTS = {
        "s": 0,

    }

    def __init__(self, date_string: str, format_: str):
        # if date_string is None:
        #     self.datetime = None
        if not isinstance(date_string, str):
            raise TypeError(f"Expected string, not {type(date_string)}")
        try:
            self.format = {
                "lid": self.LID_FORMAT,
                "label": self.LABEL_FORMAT,
            }[format_]
        except KeyError:
            raise ValueError(f"unsupported datetime format '{format_}'") from None
        self.datetime = datetime.strptime(date_string, self.format)

    def __str__(self):
        # us to ms kluge FIXME: provide str labda in format class instead
        return f"{self.datetime.strftime(self.format[:-1])[:-3]}{self.format[-1]}"

    def add_delta(self, delta: Union[str, float, int], unit: str = "s"):
        try:
            exponent = self._EXPONENTS[unit]
        except KeyError:
            # TODO: catch in outer scope and rethrow with reference to sourceline if possible
            raise ValueError(f"unrecognised unit '{unit}', expected one of {self._EXPONENTS.keys()}") from None
        if isinstance(delta, str):
            delta = float(delta)
        delta = delta*10**exponent
        self.datetime = self.datetime + timedelta(seconds=delta)


class PathManipulator:
    def __init__(self, nsmap: dict, default_prefix: str = "pds"):
        self._nsmap = nsmap
        self._default_prefix = default_prefix

    def clark_to_prefix(self, path: str):
        """
        Transforms paths provided in Clark notation (`{nsURI}tag`) to XPath-valid prefix
        notation (`nsPrefix:tag`).

        :param path: path string in Clark notation (e.g. ElementPath)
        :return: path string in prefix notation
        """
        for prefix, uri in self._nsmap.items():
            path = path.replace(f"{{{uri}}}", f"{prefix}:")
        return path

    def prefix_default_ns(self, path: str):
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


class VID:
    def __init__(self, from_string: str = None, major: int = None, minor: int = None):
        if from_string is not None:
            components = from_string.split(".")
            if not len(components):
                raise ValueError("VID string is empty!")
            self.major = components[0]
            self.minor = components[1] if len(components) > 1 else None
        elif isinstance(major, int) and isinstance(minor, int):
            self.major = major
            self.minor = minor
        else:
            raise TypeError("A VID must be provided either as a string or an int pair")

    def increment(self, which="minor"):
        if which not in ("major", "minor"):
            raise ValueError(f"expected one of 'major', 'minor'; got '{which}'")
        if which == "major":
            self.major += 1
            self.minor = 0
        else:
            self.minor = 1 if self.minor is None else self.minor + 1

    def __str__(self):
        return f"{self.major}.{self.minor}" if self.minor is not None else str(self.major)


class ProductLIDFormatter:
    LID_STRUCTURE = OrderedDict({
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
        }
    })

    def __init__(self, from_string: str = None):
        self.fields = deepcopy(self.LID_STRUCTURE)
        self.vid = None
        if from_string is not None:
            self.from_string(from_string)

    def from_string(self, lid: str):
        fields = lid.split("::")
        if len(fields) == 2:
            self.vid = VID(fields[-1])
            lid = fields[0]
        elif len(fields) > 2:
            raise ValueError(f"Invalid LID: {lid}")

        self._parse_fields(lid)

    def _parse_fields(self, lid):
        fields = lid.split(":")
        if len(fields) != 6:
            raise ValueError(f"Invalid number of LID fields ({len(fields)}): {lid}")

        self.fields["prefix"] = ":".join(fields[:3])  # urn:esa:psa
        self.fields["bundle_id"] = fields[3]
        self.fields["collection_id"] = fields[4]

        subfields = fields[5].split("_")
        # <instrument>_<processing_level>_<type>[_<subunit>]_<descriptor>_[<time1>[_<time2>]]
        if len(subfields) not in (5, 6, 7):
            raise ValueError(f"Invalid number of subfields ({len(subfields)}): "
                             f"{fields[5]}")

        pid = self.fields["product_id"]
        pid["instrument"] = subfields.pop(0)
        pid["processing_level"] = subfields.pop(0)
        pid["type"] = subfields.pop(0)

        # check for time component(s)
        try:
            time = ExoMarsDatetime(subfields[-1], "lid")
        except ValueError:
            # Future: could implement support for e.g. Sol number if required
            # For now, assume product ID only consists of basename
            # TODO: verify valid assumption for EXM/PanCam (i.e. sol number not used)
            pass
        else:
            subfields.pop()
            pid["time"] = [time]
            try:  # I don't like this nesting either...
                time = ExoMarsDatetime(subfields[-2], "lid")
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
        if not (None not in self.fields.values() and
                None not in self.fields["product_id"].values()):
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


def add_default_ns(nsmap: Dict[str, Union[str, None]]) -> Dict[str, str]:
    nsmap[DEFAULT_NS_PREFIX] = nsmap[None]
    del nsmap[None]
    return nsmap


def pt_clark(param: str):
    return f"{{{PT_NS['uri']}}}{param}"


def is_populated(elem: etree._Element):
    if elem.text is not None and bool(elem.text.strip()):
        return True
    if "xsi" in elem.nsmap and elem.attrib.get(f"{{{elem.nsmap['xsi']}}}nil", False) == "true":
        return True
    return False

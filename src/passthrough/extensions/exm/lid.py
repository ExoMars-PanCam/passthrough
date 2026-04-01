from datetime import datetime, timedelta
from typing import NamedTuple, Optional

from ...exc import PTEvalError
from ...label_tools import ATTR_PATHS
from ..pt.datetime import PDSDatetime
from ..pt.vid import VID

LID_DATETIME_FORMAT = "%Y%m%dt%H%M%S.%fz"


class LIDTime:
    """
    A class to hold and format a LID time.

    Provides duration, formatting and ordering methods
    """
    def __init__(self, start: PDSDatetime, stop: Optional[PDSDatetime] = None):
        self.start = start
        self.stop = stop

    def duration(self) -> Optional[timedelta]:
        if self.stop is None:
            return None
        return self.stop.datetime - self.start.datetime

    def __str__(self) -> str:
        if self.stop is None:
            return str(self.start)
        return f"{self.start}_{self.stop}"

    def __lt__(self, other) -> bool:
        return self.start.datetime < other.start.datetime


class PanCamPID(NamedTuple):
    """
    A class that understands PanCam PIDs.
    """
    instrument: str
    processing_level: str
    type_: str
    subunit: Optional[str]
    descriptor: str
    time: Optional[LIDTime]

    def __str__(self):
        fields = []
        for field in self:
            if field is None or not field:
                continue
            elif not isinstance(field, str):
                field = str(field)
            fields.append(field)
        return "_".join(fields)

    @classmethod
    def from_string(cls, pid: str) -> "PanCamPID":
        """Parse the product ID component of a PanCam product LID.

        Note that currently only PIDs based on (optional) start & stop times are
        supported; PIDs with trailing sol numbers are not supported.

        PIDs must adhere to the following format (optionals in square brackets):
        `<instrument>_<processing_level>_<type>[_<subunit>]_<descriptor>_[<time1>[_<time2>]]`
        """
        subfields = pid.split("_")
        if len(subfields) not in (5, 6, 7):
            raise ValueError(f"Invalid number of subfields ({len(subfields)}): {pid}")
        instrument = subfields.pop(0)
        processing_level = subfields.pop(0)
        type_ = subfields.pop(0)
        start_stop = []
        for _ in range(2):
            try:
                ss = PDSDatetime(subfields[-1], LID_DATETIME_FORMAT)
            except ValueError:
                break
            else:
                subfields.pop()
                start_stop.insert(0, ss)
        time = LIDTime(*start_stop) if start_stop else None
        descriptor = subfields.pop()
        subunit = subfields.pop() if subfields else None
        return cls(
            instrument=instrument,
            processing_level=processing_level,
            type_=type_,
            subunit=subunit,
            descriptor=descriptor,
            time=time,
        )


class ExoMarsLID(NamedTuple):
    """
    A class that understands ExoMars LIDs.
    """
    prefix: str
    bundle_id: str
    collection_id: str
    product_id: PanCamPID
    vid: Optional[VID]

    @classmethod
    def from_string(cls, lidvid: str) -> "ExoMarsLID":
        lid, *vid = lidvid.strip().split("::")
        if not vid:
            vid = None
        elif len(vid) == 1:
            vid = VID(vid[0])
        else:
            raise ValueError(f"Invalid LID(VID): {lidvid}")

        fields = lid.split(":")
        if len(fields) != 6:
            raise ValueError(f"Invalid number of LID fields ({len(fields)}): {lid}")

        prefix = ":".join(fields[:3])  # urn:esa:psa
        bundle_id = fields[3]
        collection_id = fields[4]

        # TODO: in future should add delegator class method to ProductID which
        # instantiates subclass based on bundle ID (emrsp_rm_*); subclasses to register
        # their instrument in a similar manner to ProcTools.DataProduct.
        product_id = PanCamPID.from_string(fields[5])

        return cls(
            prefix=prefix,
            bundle_id=bundle_id,
            collection_id=collection_id,
            product_id=product_id,
            vid=vid,
        )

    @classmethod
    def replace(cls, instance: "ExoMarsLID", **changes) -> "ExoMarsLID":
        args = {}
        for k in instance._fields:
            if k in changes:
                v = changes.pop(k)
            else:
                v = getattr(instance, k)
            args[k] = v
        if changes:
            raise RuntimeError(f"Field(s) not recognised: {changes}")
        return cls(**args)

    def __str__(self) -> str:
        fields = [self.prefix, self.bundle_id, self.collection_id, str(self.product_id)]
        if self.vid is not None:
            fields.append(str(self.vid))
        return ":".join(fields)

    def __eq__(self, other):
        if isinstance(other, ExoMarsLID):
            return str(self) == str(other)
        return False

    def __lt__(self, other):
        if isinstance(other, ExoMarsLID):
            return self.product_id < other.product_id
        raise TypeError(
            f"'<' not supported between instances of '{type(self)}' and '{type(other)}'"
        )


# XPath extension functions


def lid_to_browse(ctx):
    """
    Returns a LID with its first part (delimited by "_") changed to "browse".
    """
    lid = _get_source_lid(ctx)
    cid = lid.collection_id.split("_")
    cid[0] = "browse"
    browse_lid = ExoMarsLID.replace(lid, collection_id="_".join(cid))
    return str(browse_lid)


def lid_subunit(ctx):
    """
    Returns the subunit field from the LID of the source.
    """
    lid = _get_source_lid(ctx)
    subunit = lid.product_id.subunit
    if subunit is None:
        raise PTEvalError(f"Source LID does not include a subunit: '{lid}'", ctx.t_elem)
    return subunit


def lid_time(ctx):
    """
    Returns the "time" field from the LID of the source.
    """
    lid = _get_source_lid(ctx)
    time = lid.product_id.time
    if time is None:
        raise PTEvalError(f"Source LID does not include a time: '{lid}'", ctx.t_elem)
    return str(time)


def lid_to_file_name(ctx, file_type: str):
    """
    Construct a filename.
    """
    lid = _get_source_lid(ctx)
    return f"{str(lid.product_id)}{file_type}"


def _get_source_lid(ctx) -> ExoMarsLID:
    """
    Extract an ExoMars LID from the context.
    """
    lid = ctx.resources.get(ctx.s_root, None)
    if lid is None:
        # FIXME: remove dependency on ATTR_PATHS; can we move MetaElement et al to PT?
        lid = ctx.resources[ctx.s_root] = ExoMarsLID.from_string(
            ctx.s_xpath(ATTR_PATHS["lid"])[0].text
        )
    return lid

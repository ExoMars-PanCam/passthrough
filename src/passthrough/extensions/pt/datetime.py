from datetime import datetime, timedelta
from typing import Optional, Union

from lxml import etree

from ...exc import PTEvalError


class PDSDatetime:
    LABEL_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    _EXPONENTS = {
        "s": 0,
        "ms": -3,
        "microseconds": -6,
    }

    def __init__(
        self,
        date_string: Optional[str],
        format_: Optional[str] = None,
        decimals: Optional[int] = None,
    ):
        if not format_:
            format_ = self.LABEL_FORMAT
        self.format = format_

        if date_string is None:
            self.datetime = datetime.utcnow()
        elif not isinstance(date_string, str):
            raise TypeError(f"Expected string, not {type(date_string)}")
        else:
            self.datetime = datetime.strptime(date_string, self.format)

        if ".%f" not in self.format:
            decimals = None
        elif decimals is not None:
            decimals = max(0, int(decimals))
        elif date_string is not None:
            decimals = len(date_string[date_string.index(".") + 1 :])
            if date_string[-1].lower() == "z":
                decimals -= 1
        self.decimals = decimals

    def __str__(self):
        result = self.datetime.strftime(self.format)
        z = False
        if self.decimals is not None:
            if result[-1].lower() == "z":
                z = result[-1]
                result = result[:-1]
            result = result[: result.index(".") + self.decimals + 1]
            if result.endswith("."):
                result = result[:-1]
        return f"{result}{z or ''}"

    def add_delta(self, delta: Union[str, float, int], unit: str = "s"):
        try:
            exponent = self._EXPONENTS[unit]
        except KeyError:
            raise ValueError(
                f"unrecognised unit '{unit}', expected one of {self._EXPONENTS.keys()}"
            ) from None
        if isinstance(delta, str):
            delta = float(delta)
        delta = delta * 10 ** exponent
        self.datetime = self.datetime + timedelta(seconds=delta)


def datetime_add(
    ctx,
    timestamp: etree._Element,
    delta: etree._Element,
    format_: Optional[str] = None,
    decimals: Optional[int] = None,
):
    try:
        dt = PDSDatetime(timestamp[0].text, format_, decimals)
    except ValueError as e:
        raise PTEvalError(f"unable to parse datetime: {e}", ctx.t_elem) from None
    try:
        dt.add_delta(delta[0].text, unit=delta[0].attrib["unit"])
    except ValueError as e:
        raise PTEvalError(f"unable to add delta: {e}", ctx.t_elem) from None
    return str(dt)


def datetime_now(_, format_: Optional[str] = None, decimals: Optional[int] = None):
    return str(PDSDatetime(None, format_, decimals))

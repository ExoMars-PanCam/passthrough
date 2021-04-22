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
        date_string: str,
        format_: Optional[str],
        decimals: Optional[int] = None,
    ):
        if not isinstance(date_string, str):
            raise TypeError(f"Expected string, not {type(date_string)}")
        if not format_:
            format_ = self.LABEL_FORMAT
        self.format = format_
        self.datetime = datetime.strptime(date_string, self.format)

        if decimals is not None and decimals >= 0:
            self.decimals = int(decimals)
        elif ".%f" in format_:
            self.decimals = len(date_string) - date_string.index(".") - 1
            if date_string[-1].lower() == "z":
                self.decimals -= 1
        else:
            self.decimals = None

    def __str__(self):
        result = self.datetime.strftime(self.format)
        z = False
        if self.decimals is not None:
            if result[-1].lower() == "z":
                z = result[-1]
                result = result[:-1]
            # %f always yields / accepts up to 6 decimal places
            result = result[: -(6 - self.decimals)] or result

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


# TODO: rename to datetime_add
def datetime_inc(
    t_elem,
    __,
    timestamp: etree._Element,
    delta: etree._Element,
    format_: Optional[str] = None,
    decimals: Optional[int] = None,
):
    try:
        time = PDSDatetime(timestamp[0].text, format_, decimals)
    except ValueError as e:
        raise PTEvalError(f"unable to parse datetime: {e}", t_elem) from None
    try:
        time.add_delta(delta[0].text, unit=delta[0].attrib["unit"])
    except ValueError as e:
        raise PTEvalError(f"unable to add delta: {e}", t_elem) from None
    return str(time)


def datetime_now(_, __):
    # TODO:
    pass

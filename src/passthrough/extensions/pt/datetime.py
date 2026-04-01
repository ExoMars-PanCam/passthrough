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
        """
        Store a time, either the current time or a time parsed via
        date_string and (optionally) a format string. The optional
        argument, decimals, specifies how long any %f fractional
        seconds specifier should be. If decimals isn't specified
        then use some heuristics to decide what to use:

           If the current time is requested (date_string is None)
           then fix "decimals" to the default 6 digits if not specified

           If date_string is supplied then use the number of decimal
           places supplied in that.

        This is all a bit fiddly, since strftime fixes fractional
        seconds at 6 decimal places.
        """

        # Take the supplied format or, if blank, use the default.
        if not format_:
            format_ = self.LABEL_FORMAT
        self.format = format_

        # Parse the date string or, if None, use the current time.
        if date_string is None:
            self.datetime = datetime.utcnow()
            if decimals is None:
                decimals = 6
        elif not isinstance(date_string, str):
            raise TypeError(f"Expected string, not {type(date_string)}")
        else:
            self.datetime = datetime.strptime(date_string, self.format)

        # If the format string specifies fractional seconds,
        # we need to do something special. %f doesn't allow
        # for tailoring the number of decimal places. So we
        # need to work it out.
        if ".%f" not in self.format:
            # No fractional part, so no decimal places needed.
            decimals = None
        elif decimals is not None:
            # We were given a number of decimal places. Use that.
            decimals = max(0, int(decimals))
        elif date_string is not None:
            # Try to work it out from the supplied date string.

            # This isn't trivial for the general case. At this point,
            # we can be sure there's only on %f, otherwise strptime
            # would have failed. So we can try a constructive approach.
            self.decimals = 0
            while True:
                # Try to make the date string from what we've parsed.
                candidate = str(self)
                if candidate == date_string:
                    # What we've constructed matches the supplied string.
                    # Therefore the number of decimals is correct and we
                    # can break out.
                    decimals = self.decimals
                    break
                if len(candidate) > len(date_string):
                    # What we've generated is longer than the supplied
                    # string. Therefore something has gone very wrong.
                    raise ValueError("unable to determine the required fractional seconds decimal places")
                self.decimals += 1

        self.decimals = decimals

    def __str__(self):
        """
        Convert the stored time back to a string, using the
        requested format, but taking care to handle %f properly.
        """

        # Make a copy of the format string, because we're
        # likely going to change it.
        temp_format = self.format

        if "%f" in temp_format:
            # Our format has one or more fractional parts.
            if self.decimals == 0:
                # We requested no decimal places. Remove all
                # .%f and %f directives from the format string.
                temp_format = temp_format.replace(".%f", "").replace("%f", "")
            else:
                # One or more decimal places requested.
                # Get hold of the fractional time, trim it
                # to the requested number of digits and then
                # pad, just in case the requested number of
                # digits was more than %f gave us.
                fractional = self.datetime.strftime("%f")[:self.decimals].ljust(self.decimals, "0")

                # Now replace all instances of "%f" in our format string with the
                # pre-formatted fractional part we've just made.
                temp_format = temp_format.replace("%f", fractional)

        # At this point, the format string won't have any %f's,
        # so we can just go ahead and use strftime.
        return self.datetime.strftime(temp_format)

    def add_delta(self, delta: Union[str, float, int], unit: str = "s"):
        # Add an offset in seconds, milliseconds or microseconds to the
        # stored time.
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
    """
    Return a time string which is the result of adding an existing
    timestamp to a delta. The timestamp and delta are both expected
    to come from a specified XML element, where the delta has a "units"
    XML attribute specifying either "s", "ms" or "microseconds".

    Example:

    <ns:begin_timestamp pt:fetch="true()"/>
    <ns:end_timestamp pt:fill="pt:datetime.add(//ns:begin_timestamp, //ns:processing_duration)"/>

    """
    try:
        dt = PDSDatetime(timestamp[0].text, format_, decimals)
    except ValueError as e:
        raise PTEvalError(f"unable to parse datetime: {e}", ctx.t_elem) from None
    try:
        dt.add_delta(delta[0].text, unit=delta[0].attrib["unit"])
    except ValueError as e:
        raise PTEvalError(f"unable to add delta: {e}", ctx.t_elem) from None
    return str(dt)


def datetime_now(ctx, format_: Optional[str] = None, decimals: Optional[int] = None):
    """
    Return the current time with an optional format and number of decimal places.

    I'm not sure how to specify optional arguments in xml, but using them
    in order with nil for the ones you don't want to override seems to work:

    <something pt:fill="pt:datetime.now(nil, 3)"/>

    """
    return str(PDSDatetime(None, format_, decimals))

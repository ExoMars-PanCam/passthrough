from .context import get_context
from .datetime import datetime_inc, datetime_now
from .misc import self, sequence

functions = {
    "context": get_context,
    self.__name__: self,
    sequence.__name__: sequence,
    # datetime_inc.__name__.replace("_", "."): datetime_inc,
    # datetime_now.__name__.replace("_", "."): datetime_now,
    datetime_inc.__name__: datetime_inc,
    datetime_now.__name__: datetime_now,
}

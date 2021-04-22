from .context import context_get  # , context_set
from .datetime import datetime_add, datetime_now
from .misc import self, sequence

functions = {
    "context": context_get,  # TODO: consider deprecating if pt:context.set() adopted?
    context_get.__name__.replace("_", "."): context_get,
    # context_set.__name__.replace("_", "."): context_set,
    self.__name__: self,
    sequence.__name__: sequence,
    datetime_add.__name__.replace("_", "."): datetime_add,
    datetime_now.__name__.replace("_", "."): datetime_now,
}

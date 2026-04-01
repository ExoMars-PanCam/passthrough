from .context import context_get  # , context_set
from .datetime import datetime_add, datetime_now
from .vid import vid_increment
from .misc import self, sequence

functions = {
    "context":       context_get,  # TODO: consider deprecating if pt:context.set() adopted?
    "context.get":   context_get,
    # "context.set": context_set,
    "self":          self,
    "sequence":      sequence,
    "datetime.add":  datetime_add,
    "datetime.now":  datetime_now,
    "vid.increment": vid_increment,
}

resources = {"context_map": {}}

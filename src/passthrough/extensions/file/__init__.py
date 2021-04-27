def size(ctx):
    # TODO: inspect t_elem's unit to ensure return is in appropriate units
    return "TODO"


def offset(ctx):
    # TODO: offset of structure described by t_elem's parent
    return "TODO"


def md5(ctx):
    # TODO: discern file object responsible for t_elem's grand parent and query it
    return "TODO"


def datetime(ctx):
    # TODO: discern file object responsible for t_elem's grand parent and query it
    return "TODO"


def path(ctx):
    return "TODO"


functions = {
    size.__name__: size,
    offset.__name__: offset,
    md5.__name__: md5,
    datetime.__name__: datetime,
    path.__name__: path,
}

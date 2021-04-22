def file_size(t_elem, __):
    # TODO: inspect t_elem's unit to ensure return is in appropriate units
    pass


def file_offset(t_elem, __):
    # TODO: offset of structure described by t_elem's parent
    pass


def file_md5(t_elem, __):
    # TODO: discern file object responsible for t_elem's grand parent and query it
    pass


def file_datetime(t_elem, __):
    # TODO: discern file object responsible for t_elem's grand parent and query it
    pass


functions = {
    file_size.__name__.replace("_", "."): file_size,
    file_offset.__name__.replace("_", "."): file_offset,
    file_md5.__name__.replace("_", "."): file_md5,
}

from .file_handler import FileHandler, DataObject
from .. import PTContext
from ...exc import PTEvalError, PTTemplateError

"""
ToDo:
- test failure when calling file:* outside File_Area, or with unhandled File_Area
- move ext funcs to file_handler.py?
"""


def size(ctx: PTContext) -> str:
    """
    Return the file's size

    TODO: inspect t_elem's "unit" attribute to ensure return is in appropriate units
    """
    fh = _resolve_handler(ctx)
    return str(fh.file_size)


def offset(ctx: PTContext) -> str:
    """
    Looking at the example where this is mentioned (but not used), it
    looks like the intent is to fill out the offset of the start of a 
    data set within the file.
    """
    fh = _resolve_handler(ctx)
    local_id = _find_structure_lid(ctx)
    try:
        return str(fh[local_id].offset)
    except KeyError as e:
        raise PTEvalError(
            f"PDS data object with ID '{local_id}' does not appear to be managed by the"
            " file handler"
        ) from None
    except RuntimeError as e:
        raise PTTemplateError(str(e), ctx.t_elem) from None


def md5(ctx: PTContext) -> str:
    """
    Return the file's MD5 hex digest
    """
    fh = _resolve_handler(ctx)
    return str(fh.md5_checksum)


def datetime(ctx: PTContext) -> str:
    """
    Return the file's creation date and time
    """
    fh = _resolve_handler(ctx)
    return str(fh.creation_date_time)


def path(ctx: PTContext) -> str:
    """
    Return the name of the file.
    """
    fh = _resolve_handler(ctx)
    return str(fh.file_name)


def _resolve_handler(ctx: PTContext) -> FileHandler:
    fa = ctx.t_elem.xpath(
        "ancestor::*[starts-with(name(), 'File_Area_')]", namespaces=ctx.t_nsmap
    )
    if len(fa) == 0:
        raise PTTemplateError(
            "Element is not a descendant of a File_Area_*", ctx.t_elem
        )
    fa = fa[0]
    fh = ctx.resources["handlers"].get(fa, None)
    if fh is None:
        raise PTEvalError(f"No handler registered for {fa.tag}", ctx.t_elem)
    return fh


def _find_structure_lid(ctx: PTContext) -> str:
    local_id = ctx.t_elem.xpath(
        "ancestor::*/pds:local_identifier/text()", namespaces=ctx.t_nsmap
    )
    if len(local_id) == 0:
        raise PTEvalError(
            "Element is not a descendant of a data structure which provides a"
            " pds:local_identifier",
            ctx.t_elem,
        )
    return local_id[0]


functions = {
    "size":     size,
    "offset":   offset,
    "md5":      md5,
    "datetime": datetime,
    "path":     path,
}

resources = {"handlers": {}}  # Dict[etree._Element, FileHandler]

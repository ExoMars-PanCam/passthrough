from typing import Union, Sequence

from lxml import etree

from ...exc import PTEvalError


def context_get(ctx, key):
    """
    This returns a value from the map.

    <something pt:fill="py:context.get('something')"/>
    <something pt:fill="py:context.get()"/>

    """
    key = _unpack(key)
    try:
        return ctx.resources["context_map"][key]
    except KeyError:
        raise PTEvalError(f"context entry '{key}' has not been registered", ctx.t_elem)

# FIXME: How would we even call this from XML? 
# def context_set(ctx, key, value):
#     key = _unpack(key)
#     ctx.resources["context_map"][key] = value


# FIXME: should centralise this - other places would benefit from it.
def _unpack(elem: Union[str, etree._Element, Sequence[etree._Element]]):
    if isinstance(elem, list) and len(elem) == 1:
        elem = elem[0]
    if isinstance(elem, etree._Element):
        return elem.text
    return elem

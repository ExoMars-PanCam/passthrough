from typing import Union

from lxml import etree

from ...exc import PTEvalError

_context_map: dict = {}


def set_context_map(map_: dict):
    global _context_map
    _context_map = map_


def context_get(ctx, key):
    global _context_map
    key = _unpack(key)
    try:
        return _context_map[key]
    except KeyError:
        raise PTEvalError(f"context entry '{key}' has not been registered", ctx.t_elem)


# def context_set(_, key, value):
#     global _context_map
#     key = _unpack(key)
#     _context_map[key] = value


# TODO: should probably centralise this
def _unpack(elem: Union[str, etree._Element]):
    if isinstance(elem, etree._Element):
        return elem[0].text
    return elem

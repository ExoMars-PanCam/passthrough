from typing import Union

from lxml import etree

from ...exc import PTEvalError


def context_get(ctx, key):
    key = _unpack(key)
    try:
        return ctx.resources["context_map"][key]
    except KeyError:
        raise PTEvalError(f"context entry '{key}' has not been registered", ctx.t_elem)


# def context_set(ctx, key, value):
#     key = _unpack(key)
#     ctx.resources["context_map"][key] = value


# TODO: should probably centralise this
def _unpack(elem: Union[str, etree._Element]):
    if isinstance(elem, etree._Element):
        return elem[0].text
    return elem

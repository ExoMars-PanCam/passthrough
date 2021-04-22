from collections import UserDict

from ...exc import PTEvalError

_context_map: dict = {}


def set_context_map(map_: dict):
    global _context_map
    _context_map = map_


def get_context(t_elem, _, key):
    global _context_map
    try:
        return str(_context_map[key])
    except KeyError:
        raise PTEvalError(f"context entry '{key}' has not been registered", t_elem)

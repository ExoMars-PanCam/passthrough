from ...exc import PTEvalError


def self(ctx):
    return ctx.t_elem


def sequence(ctx, *args):
    ret = []
    for i, arg in enumerate(args):
        i += 1  # just used for arg num feedback
        if isinstance(arg, list):
            if len(arg) == 0:
                raise PTEvalError(
                    f"pt:sequence, argument {i}: empty node-set encountered", ctx.t_elem
                )
            elif len(arg) > 1:
                raise PTEvalError(
                    f"pt:sequence, argument {i}: node-set '{arg}' with {len(arg)}"
                    " members cannot be added to sequence as XPath does not permit"
                    " nested node-sets",
                    ctx.t_elem,
                )
            ret.append(arg[0])
        else:
            ret.append(arg)
    return ret

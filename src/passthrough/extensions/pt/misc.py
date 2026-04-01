from ...exc import PTEvalError


def self(ctx):
    """
    Return the current template element node. When called from XML,
    this will yield the string within the element. You could use this
    to generate a modified value:

    <something pt:fetch="true()" pt:fill="concat('The value was ', self())"/>

    """
    return ctx.t_elem


def sequence(ctx, *args):
    """
    Collect a sequence of XML nodes by path and return them. You could
    use this to populate an element's template with values from the input
    data:

    <something fill="pt:sequence(//something1, //something2, //something3)">
    The three values are {}, {} and {}
    </something>
    """
    ret = []
    for i, arg in enumerate(args):
        if isinstance(arg, list):
            if len(arg) == 0:
                raise PTEvalError(
                    f"pt:sequence, argument {i+1}: empty node-set encountered", ctx.t_elem
                )
            elif len(arg) > 1:
                raise PTEvalError(
                    f"pt:sequence, argument {i+1}: node-set '{arg}' with {len(arg)}"
                    " members cannot be added to sequence as XPath does not permit"
                    " nested node-sets",
                    ctx.t_elem,
                )
            ret.append(arg[0])
        else:
            ret.append(arg)
    return ret

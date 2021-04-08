from lxml import etree


class PTError(Exception):
    """Base class for passthrough exceptions."""

    def __init__(self, msg: str, t_elem: etree._Element = None):
        elem_info = (
            f" ({etree.QName(t_elem.tag).localname} @ line {t_elem.sourceline})"
            if t_elem is not None
            else ""
        )
        super().__init__(f"{msg}{elem_info}")


class PTSyntaxError(PTError):
    """A malformed PT attribute was encountered during parsing"""

    pass


class PTEvalError(PTError):
    """An error was encountered when evaluating a PT attribute"""

    pass


class PTStateError(PTError):
    """An illegal state was encountered."""

    pass


class PTFetchError(PTError):
    """An error was encountered when fetching a source element"""

    pass


class PTTemplateError(PTError):
    """An error arose from the template structure"""

    pass

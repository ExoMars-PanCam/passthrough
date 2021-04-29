# XPath expressions
PT property expressions make prolific use of XPath. The reference Python implementation of PT is based on `lxml`,
which supports XPath 1.0.

## Prefixes
Although labels conventionally make the main PDS4 data dictionary schema the default (prefix-less) namespace, XPath
does not have a notion of a default namespace. PT will therefore map the default namespace of the active source (i.e.
the XPath evaluation context) to the `pds` prefix. This means that property XPath expressions are required to prefix
elements in the default namespace with `pds`, e.g. `//pds:Time_Coordinates/pds:start_date_time`.

## Extension functions
XPath extensions are functions made available within XPath expressions either by PT itself (to address common needs)or
a client processor. Such functions are placed under the `pt` function namespace to differentiate them from the standard
array of XPath functions.

This area of PT still requires some refinement, but one helpful function worth highlighting is `pt:self()`, as seen
in the `fill` example in the section **Modifying a fetched value**. This function will always return the template
element on which the XPath expression's property is declared, and can therefore be used as a starting point to query
the template tree regardless of evaluation context / active source.

> The list of XPath extension functions provided by PT, as well as detailed instructions on how to define client-side
> extensions, will be expanded/provided as feedback is gathered and the API settles.

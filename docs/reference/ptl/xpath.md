# XPath expressions
!!! warning "Please note"
    This page is a stub and will be updated in due course, in particular with the list 
    of common XPath extension functions provided by PT.

PT property expressions make prolific use of XPath. The reference Python implementation
of PT is based on `lxml`, which supports the XPath 1.0 feature set.

## Prefixes
Although labels conventionally make the main PDS4 data dictionary schema the default 
(prefix-less) namespace, XPath does not have a notion of a default namespace. PT will 
therefore map the default namespace of the active source (i.e. the XPath evaluation 
context) to the `pds` prefix. This means that property XPath expressions are required to
prefix elements in the default namespace with `pds`, e.g. 
`//pds:Time_Coordinates/pds:start_date_time`.

## Extension functions
XPath extensions are functions made available within XPath expressions either by PT 
itself (to address common needs) or a specific mission or instrument team. Such 
functions are placed under their own function namespace to differentiate them from the 
standard array of XPath functions, and from other extension groups. The common set of 
functions provided by Passthrough can be found under the `pt` namespace.
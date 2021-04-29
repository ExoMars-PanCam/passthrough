# pt:sources
The `sources` property is used to set the active source label for an element and its descendants. Its expression is used
directly as a key to a `string -> source label` mapping provided by the client to PT on instantiation.
The resolved active source label acts as the evaluation context of the XPath expressions of other properties, and as
the source of `fetch`es. The `sources` property must therefore be declared on - or on an ancestor of - any element that
declares any other PT properties.

Given how the notion of an active source is defined, it is currently not possible to assign property expressions
declared on the same element to different source label evaluation contexts. Note, however, that as detailed in a later
section the template element *is* accessible by various means within XPath expressions, regardless of which source is
active for an element.

## Source groups
A `sources` key can map to a sequence of source labels - a "source group". In this case, the implied intent is to
duplicate the subtree starting from the given element, producing siblings that are each assigned a single label from
the source group as their active source. This behaviour is especially useful when `fetch`ing the same pluralisable class
from multiple source products, e.g. in the case of generating derived composite products where the aggregation of
certain metadata entries from each source product might be desired.

The following example shows the source group functionality used to construct a reference to each input product in the
group mapped by the `all` key.
```xml
<emrsp_rm:Processing_Inputs pt:fetch="false()">
    <emrsp_rm:Processing_Input_Identification pt:sources="all"> <!-- one entry each for all source products -->
        <emrsp_rm:type>PDS product</emrsp_rm:type>
        <emrsp_rm:Operational_Reference>
            <lid_reference/>
            <emrsp_rm:operational_vid/>
        </emrsp_rm:Operational_Reference>
    </emrsp_rm:Processing_Input_Identification>
</emrsp_rm:Processing_Inputs>
```
Notice that the cardinality of `emrsp_rm:Processing_Input_Identification` is determined at runtime by the number of
source labels assigned to the `all` group by the client. It is therefore trivial to support derived output products
that need to accommodate a variable number of input products.

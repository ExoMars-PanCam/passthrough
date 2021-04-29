# pt:required
The `required` property evaluates to a boolean flag which has similar but distinct consequences depending on whether
`fetch` is in effect.

> An element whose `required` property is evaluated to be False is referred to as an optional element, while one whose
property is evaluated to True is referred to as a required element.

## When fetching
In the context of a `fetch`, `required` is used to determine how to handle missing corresponding source elements.
If the property evaluates to True this triggers an error condition, while if it instead evaluates to False the element
(subtree) will simply be omitted from the output product. A common usage example of this feature can be seen in the
**Overview** section above.

## When not fetching
In the non-`fetch`ing context, `required` signals whether an element left empty by the client (and/or any `fill`
evaluations; see below) should be treated as an error condition (True), or if the element (subtree) should be pruned
from the output product (False).

> Elements that are "nilled out", i.e. that contain the attribute `xsi:nil="true"`, are not considered empty by PT.

An important detail in this context is that the evaluation of `required`'s XPath expression is deferred until the
post-processing stage. Thus, the expression can inspect the template label as populated by the client (which at that
point might contain relevant information about what processing has been performed) to determine whether the given
element is required to be present in the output label. For example,
```xml
<img_surface:mesh_id pt:fetch="false()" pt:required="//ex:Some_Indicative/ex:attribute == 'meshtype'" pt:sources="template"/>
```
can be read as: the `img_surface:mesh_id` attribute will be pruned by the post-processor if it is empty *and*
`ex:Some_Indicative/ex:attribute` in the output label (conventionally set as the active source via the `template`
source map key) is not equal to "meshtype".

When a class is evaluated to be optional, then for the purposes of deciding whether it should be pruned, the class is
considered empty if *any* of its children are empty. Therefore, in the case of
```xml
<emrsp_rm_pan:ISEM_Footprint pt:fetch="false()" pt:required="false()" >
    <description>Estimated location of the ISEM footprint and 1 sigma radius, based on the focus distance</description> 
    <emrsp_rm_pan:x/>
    <emrsp_rm_pan:y/>
    <emrsp_rm_pan:radius/>
</emrsp_rm_pan:ISEM_Footprint>
```
the `emrsp_rm_pan:ISEM_Footprint` class will be pruned by the post-processor if any of `x`, `y` or `radius` is empty.
The `required` property is in other words not strictly speaking inherited by child elements, but this approach is
considered preferable to the alternative where the above class would never be pruned due to the static presence of its
`desrciption` child.

If instead the class should be kept if any of its children are present, optional children should be explicitly declared
as such. The post-processor will evaluate and prune optional elements from the bottom of the hierarchy up, removing any
empty optional children from consideration by an optional parent.

Lastly, if a class is found to have a mix of empty and populated children, a warning will be issued (currently
regardless of whether the populated ones are static as for `desrciption` above). This is intended to minimise confusion
around "mysteriously missing" classes when PT is used with a human-in-the-loop (interactive) processor.

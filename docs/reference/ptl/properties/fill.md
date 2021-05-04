# pt:fill
The `fill` property can only be declared on attributes, and will set (or replace) the text contents of the
attribute with the result of its XPath expression. This functionality is commonly used to either modify a `fetch`ed
attribute, or set an attribute's value from a a non-corresponding source element (i.e. an attribute in the source which
has a different path than the template attribute). An important difference from the behaviour of `fetch` is that `fill`
will only set the text field of its target attribute - XML attributes (e.g. `unit`) are not carried over.

## Accepted types
Although ultimately a string is required, `fill`'s XPath evaluator will in practice accept a range of different
resultant types from its property expression:
- Element (the element's text field will be used)
- floats (note that working with integers in XPath is a bit cumbersome, e.g. the expression `1 + 1` evaluates to the
  float `2.0`. If integer representation is needed the builtin string function can be useful. e.g. `string(1.0 + 1)`
  evaluates to the int `2`)
- booleans (these will be "PDS-ified" to the strings `true` and `false`)

## Non-corresponding source elements
Revisiting our earlier example from the **Source groups** section, we see that there are two attributes that need to be
populated for each source: `lid_reference` and `emrsp_rm:operational_vid`. The values for both can be found in
statically known attributes in the source, but we cannot `fetch` them as they do not have the same paths as the target
template attributes. We could leave their population up to the product processor, but the "boiler plate" nature of the copy-paste
operations involved makes `fill`ing an attractive alternative, which also has the added benefit of making this part of
the template self-documenting:
```xml
<emrsp_rm:Processing_Inputs pt:fetch="false()">
    <emrsp_rm:Processing_Input_Identification pt:sources="all"> <!-- one entry each for all source products -->
        <emrsp_rm:type>PDS product</emrsp_rm:type>
        <emrsp_rm:Operational_Reference>
            <lid_reference pt:fill="//pds:Identification_Area/pds:logical_identifier/text()"/>
            <emrsp_rm:operational_vid pt:fill="//emrsp_rm:Mission_Product/emrsp_rm:operational_vid"/>
        </emrsp_rm:Operational_Reference>
    </emrsp_rm:Processing_Input_Identification>
</emrsp_rm:Processing_Inputs>
```
In light of the above discussion on accepted types, the expression used for `lid_reference` could be simplified to
omit the trailing `/text()` subexpression.

## Modifying a fetched value
In the context of a `fetch`, `fill` is evaluated last, allowing its expression to make use of an attribute's `fetch`ed
value via introspection:
```xml
<emrsp_rm:Mission_Product pt:fetch="true()" pt:sources="primary">
    ...
    <emrsp_rm:operatyonal_vid pt:fill="string(pt:self() + 1)"/>  <!-- string to ensure int result and not default float -->
    ...
</emrsp_rm:Mission_Product>
``` 
In this example we are producing an updated version of an existing product, and therefore wish to ensure that its
version identifier is incremented. This is achieved by letting the `fill` expression read in the post-`fetch` value
of the `emrsp_rm:operatyonal_vid` attribute via the `pt:self()` builtin extension function (detailed further in the
**XPath** section).

## Separation of concerns
Note that there is nothing stopping one from "putting the processor in the template" to some extent. For instance,
if a calibrated attribute needs to be populated based on a static modification of a source attribute (e.g. exposure
time from exposure ticks), this *could* be addressed by a `fill` expression. However, this approach is generally
considered bad practice from a separation of concerns perspective. There is a grey line to be drawn between boiler
plate operations and processing, and this line runs somewhere in the vicinity of the following scheme:
```xml
<Time_Coordinates pt:fetch="true()" pt:sources="primary">
    <start_date_time/> <!-- will be retrieved from the primary input label -->
    <stop_date_time pt:fetch="false()" pt:sources="template" pt:defer="true()"
                    pt:fill="pt:datetime_inc(//pds:Time_Coordinates/pds:start_date_time, //img:Exposure/img:exposure_duration)" />
</Time_Coordinates>
```
In keeping with the theme of a calibration processor, the above example shows how a `stop_date_time` can be expressed
in the template using a `defer`red `fill` expression (that is, evaluated during post-processing) employing an XPath
extension function which increments the `fetch`ed observation start time by the product processor-populated calibrated exposure
duration. This application might be considered to be within the remit of the template because it deals with the
minutiae of PDS4 datetime formatting - functionality that arguably is better suited to being encapsulated in a PT
extension function than duplicated across processors. 

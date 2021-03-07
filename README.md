# Passthrough - a PDS4 label template system 

## Installation
TODO; in the mean time, see the section **Development setup** towards the end for how to pip-install the repository in
development mode to be able to run the preliminary test script `pttesting` which exercises an SVT-1b1 raw template.


## Usage
An initial package usage example is included below; see the [pttesting script](./src/passthrough/testing/pttesting.py) 
for a working implementation.
```python
from lxml import etree
from passthrough import Template

# support for loading from pds4_tools labels is in the works
source_primary = etree.parse("~/path/to/source_primary_label.xml") 
source_secondary = etree.parse("~/path/to/source_secondary_label.xml") 
template = etree.parse("~/path/to/template_label.xml")
source_map = {
    "primary": source_primary,
    "all": (source_primary, source_secondary),
    "template": template,
}

out = Template(template, source_map, keep_template_comments=False, skip_structure_check=False)

# Populate the partial label (out.label is a regular lxml ElementTree object)
out.label.xpath("//img:Exposure/img:exposure_duration", namespaces=out.nsmap)[0].text = "2.501"

out.export("~/path/to/output/directory/")
```

The **API** section will be updated to include more detailed information in due course.


## Language documentation
### Overview
The passthrough (PT) template language supports the effective generation of PDS4 (XML) data product labels.

Distinct from many conventional template systems, PT is not designed to transform an input data structure 
directly into an output document. Rather, a template is pre-processed by the template handler into a partially 
populated label which is then handed off to the client data product processor. The client is responsible for populating 
(most of) the remaining elements before handing back control to the template handler for post-processing and export.

This usage pattern - simply referred to as "fetch, fill - fill, export" - has been deliberately chosen to leverage the 
label as its own data structure (i.e. the XML DOM), while addressing common needs when working with PDS4.
As such, key features of the system include the ability to
- pass through or redirect metadata entries (i.e. PDS4 classes and attributes) from input products ("sources")
- work with multiple source labels and groups thereof
- strictly specify the allowed permutations of the output label structure in a human friendly manner
- abstract common operations (such as dealing with LIDs and datetimes) via built-in functions
- define client-side extensions

To facilitate these features, a declarative approach is taken. PT templates foremost consist of a skeleton structure of
the PDS4 classes and attributes that comprise a given data product type (e.g. a raw image, distinct from its downstream
calibrated counterpart). In addition to these "empty" elements, XML attributes - not to be confused with PDS4 
attributes (i.e. leaf nodes; here termed *attributes*) - are added by the human template preparer to inform what pre- 
and post-processing shall be applied to specific elements and their descendants.

A key principle of PT is that a template must fully specify the structure of the output product label it describes.
In other words, a template shall act as the blueprint for its output product, and clients are actively discouraged from
amending the structural contents of the partial label generated from this template. However, tools are provided to 
allow different permutations of a label's structure to be described (i.e. some elements are only present under certain 
conditions), and repeating elements can be collapsed to increase readability of the template.

A simple example excerpt of a template might look something like:
```xml
<img:Exposure pt:fetch="true()" pt:sources="primary">
    <img:exposure_duration_count/>
    <img:exposure_duration unit="s" pt:fetch="false()"/>
    <img:exposure_type pt:required="//psa:Sub-Instrument/psa:identifier != 'HRC'"/>
</img:Exposure>
```
Here, the `img:Exposure` class is marked with `pt:fetch="true()"` and `pt:sources="primary"` to indicate that as part 
of pre-processing, its child attributes shall be populated with the values of the corresponding attributes from the 
primary source label; they will be *passed through* to the output label. As its name implies, PT emphasises
facilitating this frequent tendency under PDS4 for downstream products to repeat metadata entries of their parents. 

While `img:exposure_duration_count` above will be populated from the primary source, `img:exposure_duration`
is marked with `pt:fetch="false()"`. This indicates that the template handler expects this attribute to instead be 
populated by the client (a calibration processor, in this scenario), and will verify this as part of post-processing.

PT leverages the XML nature of PDS4 labels by making extensive use of XPath (and, as shown later, its ability to define
custom extension functions). The `img:exposure_type` attribute in this example is absent in the source label if the
data product belongs to a particular subinstrument. To inform the pre-processor of this, the element is marked as 
required on the condition that `//psa:Sub-Instrument/psa:identifier != 'HRC'`, an XPath boolean expression that 
compares the value of the relevant subinstrument attribute in the primary source label with the string literal "HRC". 
Hence the absence of `img:exposure_type` in the source will only trigger an error condition if HRC is not the active 
subinstrument.

### Element properties
> The term *element* is used as a shorthand for *XML element*. It is sometimes useful to distinguish between
> leaf node and non-leaf node elements, which in PDS4 terms are referred to as *attributes* and *classes*, 
> respectively. The term *attribute* is therefore used as a shorthand for *PDS4 attribute*; *XML attribute* is always
> spelled out.

The PT template language is based around assigning *properties* to elements of a template. These properties consist of
a single *keyword* - *expression* pair and are declared on elements in the template via XML attributes under the PT 
namespace, i.e. `pt:keyword="expression"`. The below table summarises the key characteristics of the properties that 
the language currently defines. Their individual usage patterns are described further in the next section.

| Keyword  | Expression type | Evaluated type               | Default | Inherited |
|----------|-----------------|------------------------------|---------|-----------|
| sources  | string (key)    | Sources (one or more labels) | None    | yes       |
| fetch    | XPath           | boolean                      | False   | yes       |
| multi    | XPath           | boolean or integer           | False   | no        |
| required | XPath           | boolean                      | True    | yes*      |
| fill     | XPath           | string**                     | None    | no        |
| defer    | XPath           | boolean                      | False   | no        |

\* terms and conditions apply; further details below.
\*\* `fill` expressions do not have to result in a string directly; see the relevant section below. 

Initially an element will be assigned the default value of each of the PT properties. Unless a property is explicitly
declared on a given element via an XML attribute, for some it will be inherited from the element's parent. Certain
properties are only applicable to leaf nodes (attributes), while others modify the evaluation of another property. 

During pre-processing of a template, the effective values of the PT properties of each element will be derived.
Together these constitute an element's state, which the pre-processor will check for consistency. 

### List of properties
#### sources
The `sources` property is used to set the active source label for an element and its descendants. Its expression is used 
directly as a key to a `string -> source label` mapping provided by the client to PT on instantiation.
The resolved active source label acts as the evaluation context of the XPath expressions of other properties, and as
the source of `fetch`es. The `sources` property must therefore be declared on - or on an ancestor of - any element that
declares any other PT properties.

Given how the notion of an active source is defined, it is currently not possible to assign property expressions
declared on the same element to different source label evaluation contexts. Note, however, that as detailed in a later
section the template element *is* accessible by various means within XPath expressions, regardless of which source is 
active for an element.

##### Source groups
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


#### fetch
The `fetch` property signals whether an element (or its attribute descendants, if the element is a class) should have 
its value (here: the XML element's text and XML attributes) populated by the corresponding source element. Given that 
the `fetch` property is inheritable, declaring it on a class conveys the intent that its entire subtree should be 
`fetch`ed, except where a descendant element declares otherwise. 

The definition of "corresponding source element" in the context of `fetch` is the element within the active source 
label whose path matches that of the given element in the template. Specifically, the path used follows the ElementPath 
standard, which ensures that the fully qualified tags of the element and its ancestors are taken into account rather 
than just their document order positions (commonly seen in XPath derived paths). 

It is not currently possible for `fetch` to target a specific instance of a plural element; the n-th instance of
a template element will match the n-th instance of the corresponding source element. However, it is possible to 
duplicate a singular template element's subtree for each matched source instance, using the `multi` parameter described
below. 

#### required
The `required` property evaluates to a boolean flag which has similar but distinct consequences depending on whether 
`fetch` is in effect.

> An element whose `required` property is evaluated to be False is referred to as an optional element, while one whose
property is evaluated to True is referred to as a required element.

##### When fetching
In the context of a `fetch`, `required` is used to determine how to handle missing corresponding source elements.
If the property evaluates to True this triggers an error condition, while if it instead evaluates to False the element 
(subtree) will simply be omitted from the output product. A common usage example of this feature can be seen in the 
**Overview** section above.
##### When not fetching
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

#### multi
In a similar fashion to `required`, the `multi` property functions slightly differently depending on whether it is
declared within a `fetch` context or not. 
##### When fetching
In this context `multi` is used to signal whether the pre-processor should expect to find multiple instances of an 
element in the active source, and optionally how many. An evaluated value of True (as achieved with any boolean 
XPath expression such as `true()` or even `1 = 1`) will duplicate the template element for each matched instance in the 
active source. If instead the expression evaluates to an integer, *N*, the effect is functionally equivalent to if the 
element (subtree) was repeated *N* times in the template instead, with the exception that the pre-processor will raise 
an error if the number of matched source instances is not equal to *N*.
```xml
<geom:Motion_Counter pt:fetch="true()" pt:sources="primary">
    <geom:name/>
    <local_identifier/>
    <geom:Motion_Counter_Index pt:multi="12"> 
        <geom:index_id/>
        <geom:index_value_number/>
    </geom:Motion_Counter_Index>
</geom:Motion_Counter>
```
Here, setting `multi` to `12` signals that we expect the pre-processor to find exactly 12 instances of 
`geom:Motion_Counter_Index` in the active source label. Specifying the cardinality is not strictly necessary, but in 
this example we know that the motion counter has exactly 12 indices, which we wish to express to increase the 
descriptiveness of the template and enable the additional consistency checks.
##### When not fetching
Outside the `fetch` context, the `multi` property can be used for convenience to collapse repeating (identical) 
elements in the template into a single entry. In this mode the property expression must evaluate to an integer 
(as a value of True would not be very helpful), which indicates the total number of element instances that will
be made available by the pre-processor.

#### fill
The `fill` property can only be declared on attributes, and will set (or replace) the text contents of the 
attribute with the result of its XPath expression. This functionality is commonly used to either modify a `fetch`ed 
attribute, or set an attribute's value from a a non-corresponding source element (i.e. an attribute in the source which 
has a different path than the template attribute). An important difference from the behaviour of `fetch` is that `fill` 
will only set the text field of its target attribute - XML attributes (e.g. `unit`) are not carried over.

##### Accepted types
Although ultimately a string is required, `fill`'s XPath evaluator will in practice accept a range of different 
resultant types from its property expression:
- Element (the element's text field will be used)
- floats (note that working with integers in XPath is a bit cumbersome, e.g. the expression `1 + 1` evaluates to the 
float `2.0`. If integer representation is needed the builtin string function can be useful. e.g. `string(1.0 + 1)` 
evaluates to the int `2`)
- booleans (these will be "PDS-ified" to the strings `true` and `false`)  

##### Non-corresponding source elements
Revisiting our earlier example from the **Source groups** section, we see that there are two attributes that need to be 
populated for each source: `lid_reference` and `emrsp_rm:operational_vid`. The values for both can be found in 
statically known attributes in the source, but we cannot `fetch` them as they do not have the same paths as the target 
template attributes. We could leave their population up to the client, but the "boiler plate" nature of the copy-paste 
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

##### Modifying a fetched value
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

##### Separation of concerns
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
extension function which increments the `fetch`ed observation start time by the client populated calibrated exposure 
duration. This application might be considered to be within the remit of the template because it deals with the 
minutiae of PDS4 datetime formatting - functionality that arguably is better suited to being encapsulated in a PT
extension function than duplicated across processors. 

#### defer
The `defer` property amounts to a binary flag that dictates whether an accompanying `fill` property should be evaluated
during the pre-processing (False) or the post-processing (True) stage (i.e. before or after the client has performed
element population).


### XPath expressions
PT property expressions make prolific use of XPath. The reference Python implementation of PT is based on `lxml`,
which only supports XPath 1.0.  
#### Prefixes
Although labels conventionally make the main PDS4 data dictionary schema the default (prefix-less) namespace, XPath 
does not have a notion of a default namespace. PT will therefore map the default namespace of the active source (i.e. 
the XPath evaluation context) to the `pds` prefix. This means that property XPath expressions are required to prefix 
elements in the default namespace with `pds`, e.g. `//pds:Time_Coordinates/pds:start_date_time`.
#### Extension functions
XPath extensions are functions made available within XPath expressions either by PT itself (to address common needs)or 
a client processor. Such functions are placed under the `pt` function namespace to differentiate them from the standard
array of XPath functions. 

This area of PT still requires some refinement, but one helpful function worth highlighting is `pt:self()`, as seen
in the `fill` example in the section **Modifying a fetched value**. This function will always return the template 
element on which the XPath expression's property is declared, and can therefore be used as a starting point to query 
the template tree regardless of evaluation context / active source. 

> The list of XPath extension functions provided by PT, as well as detailed instructions on how to define client-side
> extensions, will be expanded/provided as feedback is gathered and the API settles.


### API
> This section will be expanded shortly. For now, please refer to the minimal usage example in the **Usage** section.


### Template processing flow specifics
The template handler is responsible for parsing and transforming a template into a partial label which is then handed 
over to be further populated by the invoking processor. In brief, the handler will perform the following steps before
handoff:
- parse the template elements depth-first in document order
- evaluate each element's declared and inherited properties to construct its effective state (and ensure its validity)
- construct and attach any duplicated subtrees (`multi` or plural `sources` conditions)
- while visiting each element:
    - execute `fetch` if present
    - execute `fill` if present and not `defer`red
    - record any `defer`red `fill`s or non-`fetch` `required` conditions for evaluation during post-processing 

After the invoking processor has populated the remaining elements of the partial label, control is handed back to the
template handler as part of the label export process (i.e. `Template.export(...)`), where the following steps occur:
- execute any recorded `defer`red `fill`s
- evaluate any non-`fetch` `required` conditions; prune eligible optional elements
- ensure all remaining elements are populated
- if indicated: ensure the structure of the partial label has not been altered by the invoking processor after handoff
- remove unused namespace declarations (including the PT namespace)
- export the label


## Development setup
The project adopts a `setuptools` based structure and therefore can be installed in 
development mode using `pip`. From the project root directory:
    
    $ pip install -e .

~~This exposes the `ptvalidate` entry point script, which can be used to check templates for errors.~~

Currently, this exposes the `pttesting` entry point script, which serves as a simple proof of concept.


## Planned features
- Helpers on the API side for working with `File_Area_Observational`.
- Full support for logging.
- Automated tests.
- Validation entry point script capable of statically checking templates.
- Interoperability with `pds4_tools` loaded source labels.
- If needed: `strict` property which actively discards non-`required` elements: in the `fetch` context, even if a
  source element is found; in the non-`fetch` context, even if the element if populated.
- If needed: `ignore` property which allows unpopulated elements to remain in the exported label (for when a downstream 
  tool will perform modifications to the product before it is validated for correctness / ingested in the archive).
- If needed: the ability to add element XML attributes via the template (likely not needed?)
- Support for no-default-prefix XPath expressions via internal substitution (supporting XPath predicates etc. will
  require a tokenizer/parser be built, which is low on the priority list).

## ToDo (readme)
- Mention how structure checking is useful for processor testing and manual generation, but can be turned off for performance
- Mention how although the reference implementation is in Python, the API and use of XPath makes it easy to port to 
other languages.

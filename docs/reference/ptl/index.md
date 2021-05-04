# The Passthrough Template Language 
!!! warning "Please note"
    This page needs to go on a diet. Some parts will likely be moved to the 
    [background area](/background), in due course. To skip past the essay, navigate to 
    the [Passthrough properties](properties) subsection.

The passthrough (PT) template language supports the effective generation of PDS4 (XML) data product labels.

Distinct from many conventional template systems, PT is not designed to transform an input data structure
directly into an output document. Rather, a template is pre-processed by the template handler into a partially
populated label which is then handed off to the data product processor. The product processor is responsible for populating
(most of) the remaining elements before handing back control to the template handler for post-processing and export.

This usage pattern - simply referred to as "fetch, fill - fill, export" - has been deliberately chosen to leverage the
label as its own data structure (i.e. the XML DOM), while addressing common needs when working with PDS4.
As such, key features of the system include the ability to
- pass through or redirect metadata entries (i.e. PDS4 classes and attributes) from input products ("sources")
- work with multiple source labels and groups thereof
- strictly specify the allowed permutations of the output label structure in a human friendly manner
- abstract common operations (such as dealing with LIDs and datetimes) via built-in functions
- define processor-side extensions

To facilitate these features, a declarative approach is taken. PT templates foremost consist of a skeleton structure of
the PDS4 classes and attributes that comprise a given data product type (e.g. a raw image, distinct from its downstream
calibrated counterpart). In addition to these "empty" elements, XML attributes - not to be confused with PDS4
attributes (i.e. leaf nodes; here termed *attributes*) - are added by the human template preparer to inform what pre-
and post-processing shall be applied to specific elements and their descendants.

A key principle of PT is that a template must fully specify the structure of the output product label it describes.
In other words, a template shall act as the blueprint for its output product, and product processors are actively discouraged from
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
populated by the product processor (a calibration processor, in this scenario), and will verify this as part of post-processing.

PT leverages the XML nature of PDS4 labels by making extensive use of XPath (and, as shown later, its ability to define
custom extension functions). The `img:exposure_type` attribute in this example is absent in the source label if the
data product belongs to a particular subinstrument. To inform the pre-processor of this, the element is marked as
required on the condition that `//psa:Sub-Instrument/psa:identifier != 'HRC'`, an XPath boolean expression that
compares the value of the relevant subinstrument attribute in the primary source label with the string literal "HRC".
Hence the absence of `img:exposure_type` in the source will only trigger an error condition if HRC is not the active
subinstrument.

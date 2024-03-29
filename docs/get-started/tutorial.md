# Generating a product label

## The primer
In this tutorial we will write a small processor which uses a simple PDS4 "type
template" to generate data product labels.

Our processor has been tasked with adding some missing label attributes[^1] to a raw 
image product generated by a telemetry processor. Using Passthrough (PT), we can define 
a blueprint for how our modified output product should look - its type template - and 
use this to instantiate a "partial label" for the processor to populate.

From here on we will assume that you have some familiarity with PDS4 labels, XML and
Python, but the finer points will be explained as we go along.

## The input
We have been provided with two sample input products which include `img:filter_number` -
the number of the active filter as reported by our instrument. Our processor will be 
adding in the corresponding filter name, ID, bandwidth and centre wavelength attributes.

!!! warning ""
    As we are here only interested in a very small part of the input product's label
    (and PDS4 labels tend to get very long!), we will cut to the chase and hide the 
    uninteresting bits behind `<!-- ... -->` comments. Please use your imagination to
    fill in the blanks.

The sample input products differ only in the filter number they report; their structures
are:

=== "sample_input_1.xml"
    ```xml
    --8<-- "./src/get-started/sample_input_1.xml"
    ```
=== "sample_input_2.xml"
    ```xml
    --8<-- "./src/get-started/sample_input_2.xml"
    ```

## The template
Passthrough language (PTL for short) type templates look a lot like regular PDS4
labels, but with some extra XML markup thrown in. This markup takes the form of PT
"properties" - XML attributes such as `pt:fetch` that direct Passthrough in how a 
template should be processed. The values of these XML attributes are (with the exception
of `pt:sources`) XPath expressions, which most prominently are used to imbue templates
with conditional logic.

To achieve our goals we have come up with the following template:

=== "template.xml"
    ```xml
    --8<-- "./src/get-started/template.xml"
    ```

### Attribute inheritance
A key trait of PTL is the ability to *pass through* attribute values from an input
product to the output product. Above, we are declaring the `fetch` property on 
`img:filter_number`, indicating that we want PT to retrieve its value from a source 
label. The source label in question is declared by the parent class' `sources` property
to be the one given the nickname "input" - a moniker that our processor will associate
with the input product during processing.

### Optional attributes
Following on we have added in the `img:filter_name` attribute, and the absence of any 
markup here indicates that this attribute's value is expected to be populated by our 
processor.

The last three attributes also should be filled in by our processor, but there's a 
catch: knowledge of our imager's operating modes tells us that it might report the
filter number as 0 if a human has configured it incorrectly. In this case, our processor 
should just set the filter name to "UNKNOWN" and leave the remaining attributes out.

We make this condition known in the template by declaring the `required` property, 
its value determined by an XPath expression which checks whether the `img:filter_number`
of the "input" source product is equal to 0. If it is, The `img:filter_id`, 
`img:bandwidth` and `img:center_filter_wavelength` attributes can be omitted from the 
output product[^2].

## The processor
Over in Python-land, our processor will make use of Passthrough's `Template` handler 
class to pre-process the template into a partial label that can be populated.

=== "processor.py"
    ```python
    --8<-- "./src/get-started/processor.py"
    ```

After importing the `Template` class, we make sure to associate the "input" moniker for
`pt:sources` with the sample input product (specifically its path), before instantiating
the `partial` label.

With the `partial` label created we can read out its `filter_number` using an XPath 
query. This will allow us to select the correct values for the attributes we want to
populate.

After defining the range of values for our attributes (which in a more realistic 
scenario might have involved loading a dedicated calibration product), we use a loop to
populate them, taking care to omit this step if we don't have a sensible value to 
populate them with.

### Product generation flow
From the layout of the processor we can surmise that the product generation flow with 
passthrough follows three broad steps:

1. gather the input product(s) and pre-process the template into a partial label object
2. populate the remaining label attributes
3. export the completed label, allowing PT to prune any unpopulated optional attributes
and run its consistency checks.

<br/>

![Template flow diagram][template_flow]

## The results
When we run our processor, we are presented with two resultant product labels, each
corresponding to one of the sample input product labels:

=== "result_1.xml"
    ```xml
    --8<-- "./src/get-started/result_1.xml"
    ```
=== "result_2.xml"
    ```xml
    --8<-- "./src/get-started/result_2.xml"
    ```

As intended, we see that `result_2.xml`, which was created with the 0-filter 
`sample_product_2.xml` as input, omits the ID, bandwidth and centre wavelength 
attributes as we intended. Success!

## The conclusion
The scenario we have been working through in this tutorial of course only scratches the
surface of what PT and PTL can do. Type templates can grapple with multiple simultaneous
input products, automatically fill in attributes using XPath extension functions, and
instantiate and manage blank payload data structures from the template's `File_Area_*`.

But the usage pattern of working with Passthrough's `Template` class that we have 
established remains largely the same. 

In the next section we will look at where you can go from here to learn more about the
individual components of Passthrough.


[^1]: In this documentation, the terms *attribute* and *class* always refer to *PDS4
attribute* and *PDS4 class*, respectively. In other words, *XML elements*. When there
is a need to refer to *XML attributes*, this is spelled out.

[^2]: By default, all elements in a template are assumed to be required, i.e. present in
the output product, unless explicitly declared otherwise. This follows the principle 
that a type template should directly reflect the structure of the product type it 
defines. The goal is to avoid surprises for users, and allow templates to act as formal
definitions of product types and further as the interfaces between processors of a
project's product pipeline.

[template_flow]: /assets/diagrams/renders/template_flow.png
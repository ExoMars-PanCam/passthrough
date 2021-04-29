# Passthrough properties
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

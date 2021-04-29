# pt:fetch
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


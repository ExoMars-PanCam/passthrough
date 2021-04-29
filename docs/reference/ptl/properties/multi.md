# pt:multi
In a similar fashion to `required`, the `multi` property functions slightly differently depending on whether it is
declared within a `fetch` context or not.
## When fetching
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
## When not fetching
Outside the `fetch` context, the `multi` property can be used for convenience to collapse repeating (identical)
elements in the template into a single entry. In this mode the property expression must evaluate to an integer
(as a value of True would not be very helpful), which indicates the total number of element instances that will
be made available by the pre-processor.

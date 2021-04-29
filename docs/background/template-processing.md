# Template processing flow specifics
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

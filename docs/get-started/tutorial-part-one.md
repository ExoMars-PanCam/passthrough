# Generating a product label
To be written

## Temporary notes
### Alternative titles 
- Generating a product
- Using passthrough to generate a product
### Structure
- establish conventions (e.g. not including xml preamble)
- part 1: no source product(s)
  - we want to do [something] (e.g. cal metadata)
  - given template xyz
  - import Template
  - instantiate, populate, export (get a feel for the flow)
  - inspect result
- part 2: inherit from source product (+ required)
  - given source template (or just product? yes), out template now has fetch
  - also source might not have attr A, so mark out A as not required (maybe conditional,
    or is that too much?)
  - import Template
  - instantiate, populate, export
  - inspect result
  - repeat with diff source contents to see pt:required in action?
    - maybe use logging output to show that A was pruned
### Resources
```python
from lxml import etree
from passthrough import Template

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

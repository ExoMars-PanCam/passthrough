---
invisible:
- navigation # Hide navigation
- toc        # Hide table of contents
---
# Template-Driven PDS4 Data Product Generation

## Overview
The Passthrough software library seeks to provide PDS4 data processors with an 
integrated solution for generating output labels based on declarative product type 
templates. It serves as a complementary counterpart to the [PDS4 Tools][1] read-in 
library, enabling processors to interact natively with the PDS4 format without the need 
for intermediary internal product representations or separate file formats.

!!! warning ""
    Passthrough is still in its initial development phase.
    Visit the [About](about.md) page for details on its status and timeline.


Passthrough consists of a Python template [handler][2], the Passthrough template 
language (PTL) [specification][3], and a language logic extension [API][4].

[1]: https://github.com/Small-Bodies-Node/pds4_tools
[2]: reference/python-api.md
[3]: reference/ptl-spec.md
[4]: reference/extension-api.md

## Project documentation
<div markdown="1" class="pt-column2">
###[Tutorials](./get-started/installation.md) *- start here*
Hit the ground running with Passthrough, and learn how you can leverage type templates
in your own mission's product processors.
</div>
<div markdown="1" class="pt-column2">
###[How-to guides](./how-to/)
Recipes addressing common use-cases and challenges you may encounter when creating 
templates and generating labels. 
</div>
<div markdown="1" class="pt-column2 pt-clear">
###[Background](background/template-processing.md)
Explanation of the key concepts behind Passthrough, and how the system integrates with 
the product generation flow.
</div>
<div markdown="1" class="pt-column2">
###[Reference](./reference/)
Technical description the Python `Template` handler, language syntax, and extensions.
</div>
<br class="pt-clear"/>

*[PDS4]: Planetary Data System, version 4


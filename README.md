# Passthrough - Template-Driven PDS4 Data Product Generation in Python
The Passthrough software library seeks to provide PDS4 data processors with an
integrated solution for generating output labels based on declarative product type
templates. It serves as a complementary counterpart to the [PDS4 Tools][1] read-in
library, enabling processors to interact natively with the PDS4 format without the need
for intermediary internal product representations or separate file formats.

To learn more, visit the project's [documentation][2].

## Installation
The Passthrough library lives on [PyPI][3] and can be installed with
`pip`:
```commandline
pip install passthrough
```
You'll need to have installed Python 3.6 or newer, and the package will pull in `lxml` 
and `numpy` as dependencies.

## Development setup
The project uses [Poetry][4] to manage dependencies and packaging. After cloning the 
repository and installing Poetry (e.g. `pipx install poetry`), the following steps 
(executed from the project root directory) will initialise the development environment.

Create venv (substitute for the version you want to work against):
```commandline
poetry env use python3.6  
```
Fetch dependencies defined in [pyproject.toml][5] and install project in 
development mode:
```commandline
poetry install  
```    

Please refer to the Poetry documentation for further information on its usage.

## Feature roadmap
### Near term / high priority
- [ ] Documentation revamp (MkDocs, tutorial, api) - *in progress*
- [ ] Helpers on the API side for working with `File_Area_Observational` - *in progress*
- [ ] Automated test suite
- [ ] Continuous integration
### Longer term / lower priority
- [ ] Validation entry point script capable of statically checking templates
- [ ] If needed: `strict` property which actively discards non-`required` elements:
  in the `fetch` context, even if a source element is found; in the non-`fetch` context,
  even if the element is populated
- [ ] If needed: `ignore` property which allows unpopulated elements to remain in the 
  exported label (for when a downstream tool will perform modifications to the product 
  before it is validated for correctness / ingested in the archive)
- [ ] If needed: the ability to add element XML attributes via the template (unlikely?)
- [ ] Support for no-default-prefix XPath expressions via internal substitution 
  (supporting XPath predicates etc. will require a tokenizer/parser be 
  built/commandeered, which is low on the priority list)
### Completed  
- [x] Adopt Poetry for packaging and dependency management
- [x] Full support for logging
- [x] Interoperability with `pds4_tools` loaded source labels
- [x] Common label interrogation/manipulation functionality exposed for clients to use
- [x] Add support for multi-fill (fill node in node-set based on which multi branch 
  context node belongs to)
- [x] Add support for fill string formatting (if node is populated and contains a 
  {}-pair, substitute in fill result)
- [x] Create extension plugin support (3rd party XPath functions)
  
[1]: https://github.com/Small-Bodies-Node/pds4_tools
[2]: https://ExoMars-PanCam.github.io/passthrough
[3]: https://pypi.org/
[4]: https://python-poetry.org/
[5]: ./pyproject.toml
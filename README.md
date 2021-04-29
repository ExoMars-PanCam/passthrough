# Passthrough - a PDS4 label template system 

## Installation
TODO

## Development setup
The project uses [Poetry](https://python-poetry.org/) to manage dependencies and packaging.
After cloning the passthrough repository and installing Poetry (e.g. `pipx install poetry`),
the following steps (executed from the prolect root directory) will initialise the development environment:
    
    $ poetry env use python3.6  # create venv (substitute for the version you want to work against)
    $ poetry install  # fetch dependencies defined in pyproject.toml and install prolect in dev mode

Please refer to the Poetry documentation for further information on its usage.

## Planned features
- [ ] Helpers on the API side for working with `File_Area_Observational`.
- [ ] Full support for logging.
- [ ] Automated tests.
- [ ] Validation entry point script capable of statically checking templates.
- [x] Interoperability with `pds4_tools` loaded source labels.
- [x] Common label interrogation/manipulation functionality exposed for clients to use.
- [x] Adopt Poetry for packaging and dependency management.
- [ ] If needed: `strict` property which actively discards non-`required` elements: in the `fetch` context, even if a
  source element is found; in the non-`fetch` context, even if the element if populated.
- [ ] If needed: `ignore` property which allows unpopulated elements to remain in the exported label (for when a downstream
  tool will perform modifications to the product before it is validated for correctness / ingested in the archive).
- [ ] If needed: the ability to add element XML attributes via the template (likely not needed?)
- [ ] Support for no-default-prefix XPath expressions via internal substitution (supporting XPath predicates etc. will
  require a tokenizer/parser be built, which is low on the priority list).
- [x] Add support for multi-fill (fill node in node-set based on which multi branch context node belongs to)
- [x] Add support for fill string formatting (if node is populated and contains a {}-pair, substitute in fill result)

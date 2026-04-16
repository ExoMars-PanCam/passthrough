import sys
import pytest
import lxml.etree

from passthrough import Template

@pytest.fixture()
def test_path(request):
    return request.path.parent

@pytest.fixture()
def valid_source_map_1(test_path):
    return {
        "input": test_path / "sample_input_1.xml"
    }

@pytest.fixture()
def valid_source_map_2(test_path):
    return {
        "input": test_path / "sample_input_2.xml"
    }

@pytest.fixture()
def missing_input_file_source_map(test_path):
    return {
        "input": test_path / "non_existent_template.xml"
    }

@pytest.fixture()
def invalid_input_file_source_map(test_path):
    return {
        "input": test_path / "invalid_input.xml"
    }


@pytest.fixture()
def missing_template_file(test_path):
    return test_path / "non_existent_template.xml"

@pytest.fixture()
def invalid_template_file(test_path):
    return test_path / "invalid_template.xml"

@pytest.fixture()
def valid_template_file(test_path):
    return test_path / "valid_template.xml"

# This is a fairly cunning way of getting fixtures into
# a helper function without having to pass them explicitly.
# It creates and returns a closure - so when pytest implicitly
# calls the fixture function, what we get back is a new function
# which can see the requested fixtures and doesn't need them passing
# in.
@pytest.fixture()
def check_generated_output(tmp_path, test_path):
    def _check_generated_output(output_file, reference_file):
        with open(tmp_path / output_file, "r") as of:
            output = list(of)
        with open(test_path / reference_file, "r") as rf:
            reference = list(rf)
        assert output == reference, f"'{output_file}' and '{reference_file}' are not identical"
    return _check_generated_output

def test_template_constructor_no_args():
    """This test confirms that an exception is raised when the template
    constructor is called with no arguments.
    """
    with pytest.raises(TypeError, match=r"missing 2 required positional arguments: 'template' and 'source_map'"):
        t = Template()

def test_template_constructor_missing_source_map():
    """This test confirms that an exception is raised when the template
    constructor is called with just the "template" argument.
    """
    with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'source_map'"):
        t = Template(None)

def test_template_constructor_missing_template():
    """This test confirms that an exception is raised when the template
    constructor is called with just the "source_map" argument.
    """
    with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'template'"):
        t = Template(source_map=None)

def test_template_constructor_invalid_source_map():
    """This test confirms that an exception is raised when the template
    constructor is called with an invalid source map.
    FIXME: IMHO, the constructor should explicitly test this rather than
    falling through to the point where a less-comprehensible exception is
    raised.
    """
    with pytest.raises(TypeError, match=r"'NoneType' object is not iterable"):
        t = Template(None, None)

def test_template_constructor_invalid_template(valid_source_map_1):
    """This test confirms that an exception is raised when the template
    constructor is called with an invalid template argument.
    """
    with pytest.raises(TypeError, match=r"template is in an unknown label format <class 'NoneType'>"):
        t = Template(None, valid_source_map_1)

def test_template_constructor_template_not_found(valid_source_map_1, missing_template_file):
    """This test confirms that an exception is raised when the template
    constructor is called with a template argument that references a
    non-existent file.
    """
    with pytest.raises(OSError, match=f"Error reading file '{missing_template_file}': failed to load \"{missing_template_file}\": No such file or directory"):
        t = Template(missing_template_file, valid_source_map_1)

def test_template_constructor_template_invalid_xml(valid_source_map_1, invalid_template_file):
    """This test confirms that an exception is raised when the template
    file contains invalid XML.
    """
    with pytest.raises(lxml.etree.XMLSyntaxError, match="Document is empty, line 1, column 1"):
        t = Template(invalid_template_file, valid_source_map_1)

def test_template_constructor_missing_input(missing_input_file_source_map, valid_template_file):
    """This test confirms that an exception is raised when the source map
    does not identify any input file.
    """
    with pytest.raises(OSError, match=f"Error reading file '{missing_input_file_source_map['input']}': failed to load \"{missing_input_file_source_map['input']}\": No such file or directory"):
        t = Template(valid_template_file, missing_input_file_source_map)

def test_template_constructor_invalid_input(invalid_input_file_source_map, valid_template_file):
    """This test confirms that an exception is raised when the source map
    identifies a file with invalid XML.
    """
    with pytest.raises(lxml.etree.XMLSyntaxError, match="Document is empty, line 1, column 1"):
        t = Template(valid_template_file, invalid_input_file_source_map)

def test_template_constructor_template_valid(valid_source_map_1, valid_template_file):
    """This test confirms that a template can be built successfully when
    valid input is provided.
    """
    t = Template(valid_template_file, valid_source_map_1)
    assert isinstance(t, Template)

def test_getting_started(valid_template_file, valid_source_map_1, valid_source_map_2, check_generated_output, tmp_path):
    """This test confirms that the procedure identified in the
    "getting_started" documentation can be run and generates 
    the expected output.
    """
    for source_map, reference_output in (
            (valid_source_map_1, "result_1.xml"), 
            (valid_source_map_2, "result_2.xml")
    ):
        partial = Template(valid_template_file, source_map, keep_template_comments=True)

        # Determine the current product's filter number
        filter_number = partial.label.find(
            ".//img:Optical_Filter/img:filter_number", partial.nsmap
        )
        filter_number = int(filter_number.text)

        # Define the attribute values to populate for the range of filter numbers we expect
        filter_attributes = {
            "filter_name": [
                "UNKNOWN",
                "Broadband Red",
                "Broadband Green",
                "Broadband Blue",
            ],
            "filter_id": [None, "C01", "C02", "C03"],
            "bandwidth": [None, "100", "80", "120"],
            "center_filter_wavelength": [None, "640", "540", "440"],
        }

        # Populate our attributes (but only if we actually have values for them)
        for attr_name, values in filter_attributes.items():
            value = values[filter_number]
            if value is None:
                continue
            attr = partial.label.find(
                f".//img:Optical_Filter/img:{attr_name}", partial.nsmap
            )
            attr.text = value
        partial.export(tmp_path, "test_result.xml")
        check_generated_output("test_result.xml", reference_output)

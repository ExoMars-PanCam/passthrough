from passthrough import Template


def process(input_path, output_name):
    sources = {"input": input_path}
    partial = Template("./template.xml", sources, keep_template_comments=True)

    # Determine the current product's filter number
    filter_number = partial.label.find(
        "//img:Optical_Filter/img:filter_number", partial.nsmap
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
            f"//img:Optical_Filter/img:{attr_name}", partial.nsmap
        )
        attr.text = value

    # Write the completed label to disk
    partial.export("./", output_name)


if __name__ == "__main__":
    queue = {
        "./sample_input_1.xml": "result_1.xml",
        "./sample_input_2.xml": "result_2.xml",
    }
    for input_path, output_name in queue.items():
        process(input_path, output_name)

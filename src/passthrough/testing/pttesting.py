from pathlib import Path

# import pds4_tools
from lxml import etree

from ..template import Template


def cli():
    file_dir = Path(__file__).parent.resolve()
    source = etree.parse(
        str(file_dir / "pan_raw_sc_r00_observation_20201110t221840.359z.xml")
    )
    # source = pds4_tools.read(
    #     str(file_dir / "pan_raw_sc_r00_observation_20201110t221840.359z.xml"),
    #     lazy_load=True,
    #     quiet=True,
    # )
    sources = {"primary": source}

    template = file_dir / "pp-200b_sample_base_wip.xml"

    handler = Template(
        template,  # Accepts one of: Path, str, ElementTree, (pds4_tools) StructureList or Label
        sources,  # register the `pt:sources` map; values same as template (or lists thereof)
        # context_map={"toast": "good"},  # register lookups for the builtin extension `pt:context()`
        template_source_entry=True,  # create a "template" source map key referring to the partial label
        keep_template_comments=False,
        skip_structure_check=False,
    )

    elems = {
        "//img:Exposure/img:exposure_duration": "2.501",
        "//img:Device_Temperature/img:temperature_value": "25.01",
    }
    wac = {
        "//img:Optical_Filter/img:filter_name": "TEST",
        "//img:Optical_Filter/img:filter_id": "TEST",
        "//img:Optical_Filter/img:bandwidth": "100",
        "//img:Optical_Filter/img:center_filter_wavelength": "650",
    }
    hrc = {
        "//img:Focus/img:best_focus_position": "5",
    }

    if handler.label.xpath(
        "//psa:Sub-Instrument/psa:identifier = 'HRC'", namespaces=handler.nsmap
    ):
        elems.update(hrc)
    else:
        elems.update(wac)

    for path, val in elems.items():
        for instance in handler.label.xpath(path, namespaces=handler.nsmap):
            instance.text = val

    handler.export(file_dir / "out")

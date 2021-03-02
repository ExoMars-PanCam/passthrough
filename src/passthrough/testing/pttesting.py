from pathlib import Path

from lxml import etree

from ..template import Template


def cli(argv=None):
    file_dir = Path(__file__).parent.resolve()
    source = etree.parse(str(file_dir/"pan_raw_sc_r00_observation_20201110t221840.359z.xml"))
    template = etree.parse(str(file_dir/"pp-200b_sample_base_wip.xml"))
    sources = {
        "primary": source,
        "template": template,
    }

    out = Template(template, sources, context_map={"toast": "good"}, keep_template_comments=False, skip_structure_check=False)

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

    if out.label.xpath("//psa:Sub-Instrument/psa:identifier = 'HRC'", namespaces=out.nsmap):
        elems.update(hrc)
    else:
        elems.update(wac)

    for path, val in elems.items():
        for instance in out.label.xpath(path, namespaces=out.nsmap):
            instance.text = val

    out.export(file_dir/"out")

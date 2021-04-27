ATTR_PATHS_EXM = {
    "cam": "//psa:Sub-Instrument/psa:identifier",
    "filter": "//img:Optical_Filter/img:filter_number",
    "type": "//msn:Mission_Information/msn:product_type_name",
}

from .lid import lid_subunit, lid_time, lid_to_browse

functions = {
    lid_to_browse.__name__.replace("_", ".", 1): lid_to_browse,
    lid_subunit.__name__.replace("_", ".", 1): lid_subunit,
    lid_time.__name__.replace("_", ".", 1): lid_time,
}

from .lid import lid_subunit, lid_time, lid_to_browse, lid_to_file_name

functions = {
    "lid.to_browse":        lid_to_browse,
    "lid.subunit":          lid_subunit,
    "lid.time":             lid_time,
    "lid.to_file_name":     lid_to_file_name,
}

resources = {"lids": {}}  # Dict[etree._Element, ExoMarsLID]

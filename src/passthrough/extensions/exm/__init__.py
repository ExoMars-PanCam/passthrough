from .lid import lid_subunit, lid_time, lid_to_browse, lid_to_file_name

functions = {
    lid_to_browse.__name__.replace("_", ".", 1): lid_to_browse,
    lid_subunit.__name__.replace("_", ".", 1): lid_subunit,
    lid_time.__name__.replace("_", ".", 1): lid_time,
    lid_to_file_name.__name__.replace("_", ".", 1): lid_to_file_name,
}

resources = {"lids": {}}  # Dict[etree._Element, ExoMarsLID]

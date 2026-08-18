from os.path import dirname, join

from qaequilibrae.modules.network.add_network_record_dialog import AddNetworkRecordDialog


class AddLinkTypeDialog(AddNetworkRecordDialog):
    """Adds a link type to the network of the open project."""

    table = "link_types"
    id_field = "link_type_id"
    name_field = "link_type"

    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_add_link_type.ui"), qgis_project=qgis_project)

    def optional_inputs(self) -> dict:
        return {
            "description": (self.lbl_description, self.txt_description),
            "lanes": (self.lbl_lanes, self.sb_lanes),
            "lane_capacity": (self.lbl_lane_capacity, self.sb_lane_capacity),
            "speed": (self.lbl_speed, self.dsb_speed),
        }

    def add_record(self):
        records = self.existing_records()
        link_type_id = self.txt_id.text().strip()
        name = self.txt_name.text().strip()

        error = self.invalid_input(link_type_id, name, records)
        if error is not None:
            self.report(error, is_error=True)
            return

        link_types = self.project.network.link_types
        link_type = link_types.new(link_type_id)

        try:
            link_type.link_type = name
            link_type.description = self.txt_description.text().strip() or None
            # The three numbers below read "Not set" at zero, which is what an empty column means
            link_type.lanes = self.sb_lanes.value() or None
            link_type.lane_capacity = self.sb_lane_capacity.value() or None
            link_type.speed = self.dsb_speed.value() or None
            link_type.save()
        except Exception as e:
            self.__discard(link_type_id)
            self.report(self.tr("Could not add the link type: {}").format(e), is_error=True)
            return

        self.qgis_project.message_log(self.tr("Link type '{}' ({}) added to the project").format(name, link_type_id))
        self.refresh_link_editing_form()
        self.reset_form()
        self.report(self.tr("Link type '{}' added to the project").format(name))

    def __discard(self, link_type_id: str):
        """Undoes new(), which lists the link type as part of the project before it is ever saved.

        Whatever stopped the save can stop the delete that goes with it, so the list is cleaned up
        either way - leaving the link type there would hold on to the identifier for the session.
        """
        link_types = self.project.network.link_types
        try:
            link_types.delete(link_type_id)
        except Exception:
            link_types.all_types().pop(link_type_id, None)

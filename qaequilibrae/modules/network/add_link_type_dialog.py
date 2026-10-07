from os.path import dirname, join

from qaequilibrae.modules.network.add_network_record_dialog import AddNetworkRecordDialog
from qaequilibrae.modules.processing_provider.data_procedures.add_link_type import AddLinkType


class AddLinkTypeDialog(AddNetworkRecordDialog):
    """Adds a link type to the network of the open project."""

    table = "link_types"
    id_field = "link_type_id"
    name_field = "link_type"
    error_message = "Could not add the link type: {}"
    log_message = "Link type '{}' ({}) added to the project"
    success_message = "Link type '{}' added to the project"
    algorithm_type = AddLinkType

    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_add_link_type.ui"), qgis_project=qgis_project)

    def optional_inputs(self) -> dict:
        return {
            "description": (self.lbl_description, self.txt_description),
            "lanes": (self.lbl_lanes, self.sb_lanes),
            "lane_capacity": (self.lbl_lane_capacity, self.sb_lane_capacity),
            "speed": (self.lbl_speed, self.dsb_speed),
        }

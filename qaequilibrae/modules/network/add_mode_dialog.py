from os.path import dirname, join

from qaequilibrae.modules.network.add_network_record_dialog import AddNetworkRecordDialog
from qaequilibrae.modules.processing_provider.data_procedures.add_mode import AddMode


class AddModeDialog(AddNetworkRecordDialog):
    """Adds a mode to the network of the open project."""

    table = "modes"
    id_field = "mode_id"
    name_field = "mode_name"
    error_message = "Could not add the mode: {}"
    log_message = "Mode '{}' ({}) added to the project"
    success_message = "Mode '{}' added to the project"
    algorithm_type = AddMode

    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_add_mode.ui"), qgis_project=qgis_project)

    def optional_inputs(self) -> dict:
        return {
            "description": (self.lbl_description, self.txt_description),
            "pce": (self.lbl_pce, self.dsb_pce),
            "vot": (self.lbl_vot, self.dsb_vot),
            "ppv": (self.lbl_ppv, self.dsb_ppv),
        }

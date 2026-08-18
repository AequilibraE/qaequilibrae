from os.path import dirname, join

from qaequilibrae.modules.network.add_network_record_dialog import AddNetworkRecordDialog


class AddModeDialog(AddNetworkRecordDialog):
    """Adds a mode to the network of the open project."""

    table = "modes"
    id_field = "mode_id"
    name_field = "mode_name"

    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_add_mode.ui"), qgis_project=qgis_project)

    def optional_inputs(self) -> dict:
        return {
            "description": (self.lbl_description, self.txt_description),
            "pce": (self.lbl_pce, self.dsb_pce),
            "vot": (self.lbl_vot, self.dsb_vot),
            "ppv": (self.lbl_ppv, self.dsb_ppv),
        }

    def add_record(self):
        records = self.existing_records()
        mode_id = self.txt_id.text().strip()
        name = self.txt_name.text().strip()

        error = self.invalid_input(mode_id, name, records)
        if error is not None:
            self.report(error, is_error=True)
            return

        modes = self.project.network.modes
        mode = modes.new(mode_id)
        mode.mode_name = name
        mode.description = self.txt_description.text().strip() or None
        mode.pce = self.dsb_pce.value()
        mode.vot = self.dsb_vot.value()
        mode.ppv = self.dsb_ppv.value()

        try:
            modes.add(mode)
        except Exception as e:
            self.report(self.tr("Could not add the mode: {}").format(e), is_error=True)
            return

        self.qgis_project.message_log(self.tr("Mode '{}' ({}) added to the project").format(name, mode_id))
        self.refresh_link_editing_form()
        self.reset_form()
        self.report(self.tr("Mode '{}' added to the project").format(name))

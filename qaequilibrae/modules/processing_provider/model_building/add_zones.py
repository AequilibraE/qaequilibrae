from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class AddZones(QAequilibraEProcessingAlgorithm):
    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_add_zones

        super().__init__(
            partial(run_add_zones, get_aequilibrae_menu_instance()),
            "add_project_zones",
            self.tr("Add zoning data"),
            self.tr("Model building"),
            "model_building",
            self.tr("Add project zones"),
            ["add", "project", "zones", "zoning"],
        )

    def createInstance(self):
        return AddZones()

    def tr(self, message):
        return trlt("AddZones", message)

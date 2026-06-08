from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class AddConnectors(QAequilibraEProcessingAlgorithm):
    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_add_connectors import run_add_connectors

        super().__init__(
            partial(run_add_connectors, get_aequilibrae_menu_instance()),
            "addcentroidconnector",
            self.tr("Add centroid connectors"),
            self.tr("Model building"),
            "model_building",
            self.tr("Adds centroid connectors for one or all modes."),
            ["centroid", "connector", "network"],
        )

    def createInstance(self):
        return AddConnectors()

    def tr(self, message):
        return trlt("AddConnectors", message)

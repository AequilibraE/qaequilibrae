from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class AddConnectors(QAequilibraEProcessingAlgorithm):
    def __init__(self):
        from qaequilibrae.menu_actions.action_add_connectos import run_add_connectors

        super().__init__(
            run_add_connectors,
            "addcentroidconnector",
            self.tr("Add centroid connectors"),
            self.tr("1. Model Building"),
            "modelbuilding",
            self.tr("Adds centroid connectors for one or all modes."),
            [],
        )

    def createInstance(self):
        return AddConnectors()

    def tr(self, message):
        return trlt("AddConnectors", message)

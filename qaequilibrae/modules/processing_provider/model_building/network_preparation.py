from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class PrepareNetwork(QAequilibraEProcessingAlgorithm):
    def __init__(self):
        from qaequilibrae.modules.menu_actions import prepare_network

        super().__init__(
            partial(prepare_network, get_aequilibrae_menu_instance()),
            "prepare_network",
            self.tr("Network preparation"),
            self.tr("Model building"),
            "model_building",
            self.tr("Prepares network for import"),
            ["preparation", "network"],
        )

    def createInstance(self):
        return PrepareNetwork()

    def tr(self, message):
        return trlt("PrepareNetwork", message)

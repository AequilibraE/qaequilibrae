from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class AddMode(QAequilibraEProcessingAlgorithm):
    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_add_mode

        super().__init__(
            partial(run_add_mode, get_aequilibrae_menu_instance()),
            "add_mode",
            self.tr("Add mode"),
            self.tr("Data"),
            "data",
            self.tr("Adds a mode to the network of the open project"),
            ["mode", "modes", "network", "add", "new"],
        )

    def createInstance(self):
        return AddMode()

    def tr(self, message):
        return trlt("AddMode", message)

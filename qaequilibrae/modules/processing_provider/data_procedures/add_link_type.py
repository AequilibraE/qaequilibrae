from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class AddLinkType(QAequilibraEProcessingAlgorithm):
    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_add_link_type

        super().__init__(
            partial(run_add_link_type, get_aequilibrae_menu_instance()),
            "add_link_type",
            self.tr("Add link type"),
            self.tr("Data"),
            "data",
            self.tr("Adds a link type to the network of the open project"),
            ["link type", "link_type", "network", "add", "new"],
        )

    def createInstance(self):
        return AddLinkType()

    def tr(self, message):
        return trlt("AddLinkType", message)

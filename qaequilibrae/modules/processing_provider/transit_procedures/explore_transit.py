from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class ExploreTransit(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_pt_explore

        super().__init__(
            partial(run_pt_explore, get_aequilibrae_menu_instance()),
            "explore_transit",
            self.tr("Explore transit"),
            self.tr("Transit"),
            "transit",
            "",
            ["public transport", "transit", "explore", "view"],
        )

    def createInstance(self):
        return ExploreTransit()

    def tr(self, message):
        return trlt("ExploreTransit", message)

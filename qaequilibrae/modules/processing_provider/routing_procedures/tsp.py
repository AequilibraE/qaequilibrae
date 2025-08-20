from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class RunTSP(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_tsp

        super().__init__(
            partial(run_tsp, get_aequilibrae_menu_instance()),
            "run_tsp",
            self.tr("Traveling salesman problem"),
            self.tr("Routing"),
            "routing",
            "Runs a TSP",
            ["optimization", "tsp", "routing", "problem"],
        )

    def createInstance(self):
        return RunTSP()

    def tr(self, message):
        return trlt("RunTSP", message)

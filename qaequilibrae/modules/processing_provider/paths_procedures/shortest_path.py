from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class ShortestPath(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_shortest_path

        super().__init__(
            partial(run_shortest_path, get_aequilibrae_menu_instance()),
            "shortest_path",
            self.tr("Shortest path"),
            self.tr("Path computation"),
            "path_computation",
            "",
            ["shortest", "path"],
        )

    def createInstance(self):
        return ShortestPath()

    def tr(self, message):
        return trlt("ShortestPath", message)

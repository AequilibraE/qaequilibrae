from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class SkimViewer(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import load_skim_viewer

        super().__init__(
            partial(load_skim_viewer, get_aequilibrae_menu_instance()),
            "skim_viewer",
            self.tr("Skim viewer"),
            self.tr("Path computation"),
            "path_computation",
            "",
            ["skim", "view", "visualize"],
        )

    def createInstance(self):
        return SkimViewer()

    def tr(self, message):
        return trlt("SkimViewer", message)

from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class VisualizeData(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_show_project_data

        super().__init__(
            partial(run_show_project_data, get_aequilibrae_menu_instance()),
            "visualize_data",
            self.tr("Visualize data"),
            self.tr("Mapping"),
            "mapping_procedures",
            "",
            ["viewer", "matrix", "data"],
        )

    def createInstance(self):
        return VisualizeData()

    def tr(self, message):
        return trlt("VisualizeData", message)

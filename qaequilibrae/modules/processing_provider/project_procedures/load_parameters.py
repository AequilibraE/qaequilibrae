from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class LoadProjectParameters(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_change_parameters

        super().__init__(
            partial(run_change_parameters, get_aequilibrae_menu_instance()),
            "load_parameters",
            self.tr("Parameters"),
            self.tr("Project"),
            "project_procedures",
            self.tr("Access project parameters"),
            ["load", "project", "parameters"],
        )

    def createInstance(self):
        return LoadProjectParameters()

    def tr(self, message):
        return trlt("LoadProjectParameters", message)

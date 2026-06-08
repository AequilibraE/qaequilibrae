from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class LoadProjectLogFile(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import show_log

        super().__init__(
            partial(show_log, get_aequilibrae_menu_instance()),
            "load_logfile",
            self.tr("Logfile"),
            self.tr("Project"),
            "project_procedures",
            self.tr("Access project logfile"),
            ["load", "project", "logfile", "log"],
        )

    def createInstance(self):
        return LoadProjectLogFile()

    def tr(self, message):
        return trlt("LoadProjectLogFile", message)

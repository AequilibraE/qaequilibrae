from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class RunProcedures(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_run_module import run_module

        super().__init__(
            partial(run_module, get_aequilibrae_menu_instance()),
            "runprocedures",
            self.tr("Run procedures"),
            self.tr("Project"),
            "project_procedures",
            self.tr("Run model procedures"),
            ["run procedures", "procedures"],
        )

    def createInstance(self):
        return RunProcedures()

    def tr(self, message):
        return trlt("RunProcedures", message)

from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class CreateScenarios(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import create_scenarios

        super().__init__(
            partial(create_scenarios, get_aequilibrae_menu_instance()),
            "createscenarios",
            self.tr("Create scenarios"),
            self.tr("Project"),
            "project_procedures",
            self.tr("Create model scenarios"),
            ["project", "model", "scenarios"],
        )

    def createInstance(self):
        return CreateScenarios()

    def tr(self, message):
        return trlt("CreateScenarios", message)

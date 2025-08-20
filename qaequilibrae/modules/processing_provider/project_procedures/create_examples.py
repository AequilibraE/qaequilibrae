from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class CreateExamples(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import show_log

        super().__init__(
            partial(show_log, get_aequilibrae_menu_instance()),
            "create_examples",
            self.tr("Create examples"),
            self.tr("Project"),
            "project_procedures",
            self.tr("Create AequilibraE examples."),
            ["create", "examples", "create examples", "project"],
        )

    def createInstance(self):
        return CreateExamples()

    def tr(self, message):
        return trlt("CreateExamples", message)

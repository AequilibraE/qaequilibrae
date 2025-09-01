from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class OpenProject(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.load_project_action import run_load_project

        super().__init__(
            partial(run_load_project, get_aequilibrae_menu_instance()),
            "open_project",
            self.tr("Open project"),
            self.tr("Project"),
            "project_procedures",
            self.tr("Open AequilibraE project"),
            ["open", "project", "open project"],
        )

    def createInstance(self):
        return OpenProject()

    def tr(self, message):
        return trlt("OpenProject", message)

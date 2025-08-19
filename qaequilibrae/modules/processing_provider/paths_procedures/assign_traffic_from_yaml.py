from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class TrafficAssignYAML(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_traffic_assignment import run_traffic_assig

        super().__init__(
            partial(run_traffic_assig, get_aequilibrae_menu_instance()),
            "assignmentfromyaml",
            self.tr("Traffic assignment from file"),
            self.tr("3. Paths and assignment"),
            "pathsandassignment",
            "Runs traffic assignment",
            ["traffic assignment", "assignment"],
        )

    # def shortHelpString(self):
    #     help_messages = [
    #         self.tr("Runs traffic assignment using a YAML configuration file."),
    #         self.tr("Example of valid configuration is provided in the plugin documentation."),
    #     ]
    #     return "\n".join(help_messages)

    def createInstance(self):
        return TrafficAssignYAML()

    def tr(self, message):
        return trlt("TrafficAssignYAML", message)

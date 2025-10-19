from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class TrafficAssignment(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_traffic_assignment import run_traffic_assig

        super().__init__(
            partial(run_traffic_assig, get_aequilibrae_menu_instance()),
            "traffic_assignment",
            self.tr("Traffic assignment"),
            self.tr("Traffic assignment"),
            "traffic_assignment",
            "Runs traffic assignment",
            ["traffic", "assignment"],
        )

    def createInstance(self):
        return TrafficAssignment()

    def tr(self, message):
        return trlt("TrafficAssignment", message)

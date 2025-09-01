from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class ProjectFromLayer(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.create_networks import run_create_transponet

        super().__init__(
            partial(run_create_transponet, get_aequilibrae_menu_instance()),
            "projectfromlayer",
            self.tr("Create project from link layer"),
            self.tr("Model building"),
            "model_building",
            self.tr("Creates an AequilibraE project from a given link layer"),
            ["layer", "project", "create"],
        )

    def createInstance(self):
        return ProjectFromLayer()

    def tr(self, message):
        return trlt("ProjectFromLayer", message)

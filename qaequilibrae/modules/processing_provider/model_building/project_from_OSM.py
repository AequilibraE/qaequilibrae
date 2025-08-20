from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class ProjectFromOSM(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.project_from_osm_action import project_from_osm

        super().__init__(
            partial(project_from_osm, get_aequilibrae_menu_instance()),
            "projectfromosm",
            self.tr("Create project from OSM"),
            self.tr("Model building"),
            "model_building",
            self.tr("Creates an AequilibraE project from OpenStreetMap"),
            ["OSM", "openstreetmap", "create", "project"],
        )

    def createInstance(self):
        return ProjectFromOSM()

    def tr(self, message):
        return trlt("ProjectFromOSM", message)

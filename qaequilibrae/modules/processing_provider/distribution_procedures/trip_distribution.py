from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class TripDistribution(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_distribution_models

        super().__init__(
            partial(run_distribution_models, get_aequilibrae_menu_instance()),
            "trip_distribution",
            self.tr("Trip distribution"),
            self.tr("Trip distribution"),
            "trip_distribution",
            "",
            ["trip", "distribution", "gravity", "ipf"],
        )

    def createInstance(self):
        return TripDistribution()

    def tr(self, message):
        return trlt("TripDistribution", message)

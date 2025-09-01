from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class RouteChoice(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_route_choice

        super().__init__(
            partial(run_route_choice, get_aequilibrae_menu_instance()),
            "route_choice",
            self.tr("Route choice"),
            self.tr("Route choice"),
            "route_choice",
            "",
            ["route", "choice", "route choice"],
        )

    def createInstance(self):
        return RouteChoice()

    def tr(self, message):
        return trlt("RouteChoice", message)

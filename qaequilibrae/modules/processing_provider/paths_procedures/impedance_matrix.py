from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class ImpedanceMatrix(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_dist_matrix

        super().__init__(
            partial(run_dist_matrix, get_aequilibrae_menu_instance()),
            "impedance_matrix",
            self.tr("Impedance matrix"),
            self.tr("Path computation"),
            "path_computation",
            "",
            ["skim", "impedance", "matrix"],
        )

    def createInstance(self):
        return ImpedanceMatrix()

    def tr(self, message):
        return trlt("ImpedanceMatrix", message)

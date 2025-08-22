from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class DesireLines(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_desire_lines

        super().__init__(
            partial(run_desire_lines, get_aequilibrae_menu_instance()),
            "desire_lines",
            self.tr("Desire lines"),
            self.tr("Mapping"),
            "mapping_procedures",
            "",
            ["line", "desire", "delaunay"],
        )

    def createInstance(self):
        return DesireLines()

    def tr(self, message):
        return trlt("DesireLines", message)

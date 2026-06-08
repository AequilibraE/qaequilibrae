from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class StackedBandwidth(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_stacked_bandwidths

        super().__init__(
            partial(run_stacked_bandwidths, get_aequilibrae_menu_instance()),
            "stacked_bandwidths",
            self.tr("Stacked bandwidth"),
            self.tr("Mapping"),
            "mapping_procedures",
            "",
            ["bandwidth", "visualization", "flow", "map"],
        )

    def createInstance(self):
        return StackedBandwidth()

    def tr(self, message):
        return trlt("StackedBandwidth", message)

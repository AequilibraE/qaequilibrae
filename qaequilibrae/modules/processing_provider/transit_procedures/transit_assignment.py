from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class TransitAssignment(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_pt_skim import run_pt_skim

        super().__init__(
            partial(run_pt_skim, get_aequilibrae_menu_instance()),
            "transit_assignment",
            self.tr("Skimming and assignment"),
            self.tr("Transit"),
            "transit",
            "Runs transit assignment",
            ["public transport", "transit", "assignment", "skimming", "skim"],
        )

    def createInstance(self):
        return TransitAssignment()

    def tr(self, message):
        return trlt("TransitAssignment", message)

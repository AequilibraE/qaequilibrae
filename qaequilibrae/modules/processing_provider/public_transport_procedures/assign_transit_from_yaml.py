from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class TransitAssignYAML(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_pt_skim import run_pt_skim

        super().__init__(
            partial(run_pt_skim, get_aequilibrae_menu_instance()),
            "ptassignfromyaml",
            self.tr("Transit assignment from file"),
            self.tr("4. Public Transport"),
            "publictransport",
            "Runs transit assignment",
            ["public transport", "transit", "assignment"],
        )

    def createInstance(self):
        return TransitAssignYAML()

    def tr(self, message):
        return trlt("ptAssignYAML", message)

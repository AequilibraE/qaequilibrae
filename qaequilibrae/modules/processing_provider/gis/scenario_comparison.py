from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class ScenarioComparison(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_scenario_comparison

        super().__init__(
            partial(run_scenario_comparison, get_aequilibrae_menu_instance()),
            "scenario_comparison",
            self.tr("Scenario comparison"),
            self.tr("Mapping"),
            "mapping_procedures",
            "",
            ["scenario", "comparison", "compare"],
        )

    def createInstance(self):
        return ScenarioComparison()

    def tr(self, message):
        return trlt("ScenarioComparison", message)

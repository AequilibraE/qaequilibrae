from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class SimpleTag(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions import run_tag

        super().__init__(
            partial(run_tag, get_aequilibrae_menu_instance()),
            "simple_tag",
            self.tr("Simple tag"),
            self.tr("Mapping"),
            "mapping_procedures",
            "",
            ["tag"],
        )

    def createInstance(self):
        return SimpleTag()

    def tr(self, message):
        return trlt("SimpleTag", message)

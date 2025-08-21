from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class ImportGTFS(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_pt_import_gtfs import run_import_gtfs

        super().__init__(
            partial(run_import_gtfs, get_aequilibrae_menu_instance()),
            "import_gtfs",
            self.tr("Import GTFS"),
            self.tr("Transit"),
            "transit",
            self.tr("Adds transit routes from a GTFS to an existing AequilibraE project."),
            ["public transport", "import", "GTFS", "transit"],
        )

    def createInstance(self):
        return ImportGTFS()

    def tr(self, message):
        return trlt("ImportGTFS", message)

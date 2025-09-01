from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class ImportMatrix(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_import_matrices import load_matrices

        super().__init__(
            partial(load_matrices, get_aequilibrae_menu_instance()),
            "import_matrix",
            self.tr("Import matrices"),
            self.tr("Data"),
            "data",
            self.tr("Saves matrix from open layer into a *.omx file"),
            ["import", "matrix", "omx", "matrices"],
        )

    def createInstance(self):
        return ImportMatrix()

    def tr(self, message):
        return trlt("ImportMatrix", message)

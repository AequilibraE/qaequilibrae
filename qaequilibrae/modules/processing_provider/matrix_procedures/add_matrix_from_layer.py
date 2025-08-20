from functools import partial

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


class MatrixFromLayer(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        from qaequilibrae.modules.menu_actions.action_import_matrices import load_matrices

        super().__init__(
            partial(load_matrices, get_aequilibrae_menu_instance()),
            "exportmatrixasomx",
            self.tr("Save matrix from layer in existing file"),
            self.tr("Data"),
            "data",
            "Saves a layer to an existing *.omx file",
            ["export", "matrix", "omx"],
        )

    def createInstance(self):
        return MatrixFromLayer()

    def tr(self, message):
        return trlt("AddMatrixFromLayer", message)

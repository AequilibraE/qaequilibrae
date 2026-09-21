from qgis.core import QgsProcessingAlgorithm

from qaequilibrae.i18n.translate import trlt

class OpenAequilibraeProjectAlgorithm(QgsProcessingAlgorithm):
    """ Open a new Aequilibrae project"""

    def name(self) -> str:
        return "openAequilibraeProject"

    def displayName(self) -> str:
        return "Open Aequilibrae Project"

    def group(self) -> str:
        # FIXME: is this the right group?
        return self.tr("Model building")

    def groupId(self) -> str:
        return "model_building"

    def createInstance(self) -> "OpenAequilibraeProjectAlgorithm":
        return OpenAequilibraeProjectAlgorithm()

    def tr(self, message):
        return trlt("OpenAequilibraeProject", message)
import importlib.util as iutil
import sys

from qgis._core import QgsProcessingContext, QgsProcessingFeedback
from qgis.core import QgsProcessingAlgorithm

from qaequilibrae.i18n.translate import trlt


class TripLengthDistribution(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        self.addParameter()

    def processAlgorithm(self, parameters, context, feedback):
        # Checks if we have AequilibraE installed
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix
        import matplotlib.pyplot as plt

        return {"Output": "DONE!"}

    def name(self):
        return self.tr("Trip length distribution")

    def displayName(self) -> str:
        return self.tr("Trip length distribution")

    def group(self) -> str:
        return super().group()

    def groupId(self) -> str:
        return super().groupId()

    def shortHelpString(self):
        return self.tr("Creates a trip-length distribution histogram and save in an output folder.")

    def createInstance(self):
        return TripLengthDistribution()

    def tr(self, message):
        return trlt("TripLengthDistribution", message)

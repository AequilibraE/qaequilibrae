from typing import Any, Dict
from qgis._core import QgsProcessingContext, QgsProcessingFeedback
from qgis.core import QgsProcessingAlgorithm

from qaequilibrae.i18n.translate import trlt

class TripLengthDistribution(QgsProcessingAlgorithm):
    def initAlgorithm(self, configuration: Dict[str, Any] = ...) -> None:
        return super().initAlgorithm(configuration)
    
    def processAlgorithm(self, parameters: Dict[str, Any], context: QgsProcessingContext, feedback: QgsProcessingFeedback | None) -> Dict[str, Any]:
        return super().processAlgorithm(parameters, context, feedback)
    
    def name(self):
        return self.tr("Trip length distribution")
    
    def displayName(self) -> str:
        return self.tr("Trip length distribution")
    
    def group(self) -> str:
        return super().group()
    
    def groupId(self) -> str:
        return super().groupId()
    
    def createInstance(self) -> QgsProcessingAlgorithm | None:
        return super().createInstance()
    
    def tr(self, message):
        return trlt("TripLengthDistribution", message)
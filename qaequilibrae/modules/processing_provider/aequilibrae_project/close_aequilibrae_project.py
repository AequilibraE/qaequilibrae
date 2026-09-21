from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsProcessingParameterFile,
    Qgis
    )

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.aequilibrae_project.qgs_processing_parameter_aequilibrae_project import QgsProcessingParameterAequilibraeProject

class CloseAequilibraeProjectAlgorithm(QgsProcessingAlgorithm):
    """ Close an Aequilibrae project"""

    def initAlgorithm(self, config: dict | None = None) -> None:
        # TODO: add boolean for whether closed correctly?
        """Declare all input parameters and output sinks"""
        self.addParameter(QgsProcessingParameterAequilibraeProject(
            "INPUT",
            "Input project",
        ))


    def processAlgorithm(self, parameters: dict, context: QgsProcessingContext, feedback: QgsProcessingFeedback) -> dict:
        """ Open a new Aequilibrae project """
        project = self.parameterAsSource(parameters, "INPUT", context)

        if feedback.isCanceled():
            return {}
        
        project.close()
        
        return {}

    def name(self) -> str:
        return "closeAequilibraeProject"

    def displayName(self) -> str:
        return "Close Aequilibrae Project"

    def group(self) -> str:
        # FIXME: is this the right group?
        return self.tr("Aequilibrae Project")

    def groupId(self) -> str:
        return "aequilibrae_project"

    def createInstance(self) -> "CloseAequilibraeProjectAlgorithm":
        return CloseAequilibraeProjectAlgorithm()

    def tr(self, message):
        return trlt("CloseAequilibraeProject", message)
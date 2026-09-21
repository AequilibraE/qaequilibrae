from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsProcessingParameterFile,
    Qgis
    )

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.qaequilibrae.modules.processing_provider.qgs_processing_output_aequilibrae_project import QgsProcessingOutputAequilibraeProject

class OpenAequilibraeProjectAlgorithm(QgsProcessingAlgorithm):
    """ Open a new Aequilibrae project"""

    def initAlgorithm(self, config: dict | None = None) -> None:
        # FIXME: what to do with config dict?
        """Declare all input parameters and output sinks"""
        self.addParameter(QgsProcessingParameterFile(
            "INPUT",
            "Input filename",
            behavior=Qgis.ProcessingFileParameterBehavior.Folder
        ))

        self.addOutput(
            QgsProcessingOutputAequilibraeProject(name="AEQUILIBRAEPROJECT", description=self.tr("Aequilibrae project"))
        )

    def processAlgorithm(self, parameters: dict, context: QgsProcessingContext, feedback: QgsProcessingFeedback) -> dict:
        """ Open a new Aequilibrae project """
        project_path = self.parameterAsSource(parameters, "INPUT", context)

        if feedback.isCanceled():
            return {}

        project = Project()
        
        try:
            project.open(project_path)
        except FileNotFoundError as e:
            if e.args[0] == "Model does not exist. Check your path and try again":
                raise QgsProcessingException("Folder does not contain an Aequilibrae model. Check your path and try again.")
            else:
                raise e
        
        if feedback.isCanceled():
            return {}

        return{"OUTPUT": project}

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
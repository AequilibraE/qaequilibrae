import importlib.util as iutil
import sys

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterString,
    QgsProcessingParameterFolderDestination,
)

from qaequilibrae.i18n.translate import trlt


class ProjectFromOSM(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterString("place_name", self.tr("Place name"), multiLine=False))
        self.addParameter(
            QgsProcessingParameterFolderDestination("project_path", self.tr("Output folder"), createByDefault=True)
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae import Project

        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)
        feedback.pushInfo(self.tr("Creating project"))

        project = Project()
        project.new(parameters["project_path"])

        project.network.create_from_osm(place_name=parameters["place_name"])

        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        feedback.pushInfo(self.tr("Closing project"))
        project.close()

        return {"Output": parameters["project_path"]}

    def name(self):
        return "projectfromosm"

    def displayName(self):
        return self.tr("Create project from OSM")

    def group(self):
        return self.tr("1. Model Building")

    def groupId(self):
        return "modelbuilding"

    def shortHelpString(self):
        return self.tr("Creates an AequilibraE project from OpenStreetMap")

    def createInstance(self):
        return ProjectFromOSM()

    def tr(self, message):
        return trlt("ProjectFromOSM", message)

import importlib.util as iutil
import pandas as pd
import sys
from os.path import join
from string import ascii_lowercase
from shapely.wkt import loads as load_wkt

from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterString

from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.i18n.translate import trlt


class ProjectFromOSM(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                "OSM_place",
                self.tr("Place name (OSM search)"),
                multiLine=False,
                defaultValue=""
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "dst",
                self.tr("Output folder"),
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=standard_path(),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "project_name",
                self.tr("Project name"),
                multiLine=False,
                defaultValue="new_project"
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae import Project

        feedback.pushInfo(self.tr("Creating project"))
        project_path = join(parameters["dst"], parameters["project_name"])
        project = Project()
        project.new(project_path)

        project.network.create_from_osm(place_name=parameters["OSM_place"])

        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        feedback.pushInfo(self.tr("Closing project"))

        return {"Output": project_path}

    def name(self):
        return self.tr("Create project from OSM")

    def displayName(self):
        return self.tr("Create project from OSM")

    def group(self):
        return ("01-"+self.tr("Model Building"))

    def groupId(self):
        return ("01-"+self.tr("Model Building"))

    def shortHelpString(self):
        return self.tr("Create an AequilibraE project from OpenStreetMap")

    def createInstance(self):
        return ProjectFromOSM()

    def tr(self, message):
        return trlt("ProjectFromOSM", message)

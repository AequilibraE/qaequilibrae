import importlib.util as iutil
import sys

from datetime import datetime as dt

from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterString, QgsProcessingParameterBoolean

from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.i18n.translate import trlt


class ImportGTFS(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "gtfs_file",
                self.tr("GTFS file (.zip)"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="",
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "agency",
                self.tr("Agency to import"), 
                multiLine=False
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "gtfs_date",
                self.tr("Date to import (YYYY-MM-DD)"), 
                multiLine=False, 
                defaultValue="2024-01-01"
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                "map_match",
                self.tr("map matching of PT lines on the aequilibrae project network"),
                defaultValue=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "project",
                self.tr("Project path"),
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=standard_path(),
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        
        if parameters["map_match"]:
            i=4
        else:
            i=3
        
        feedback = QgsProcessingMultiStepFeedback(i, model_feedback)
        
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))
        
        from aequilibrae.project import Project
        from aequilibrae.transit import Transit
        
        feedback.pushInfo(self.tr("Opening project"))
        
        # Opening project
        project = Project()
        project.open(parameters["project"])
        feedback.setCurrentStep(1)
        feedback.pushInfo(" ")
        
        # Importing GTFS
        feedback.pushInfo(self.tr("Importing GTFS"))
        data = Transit(project)
        transit = data.new_gtfs_builder(agency=parameters["agency"], file_path=parameters["gtfs_file"])
        transit.load_date(parameters["gtfs_date"])
        feedback.setCurrentStep(2)
        feedback.pushInfo(" ")
        
        # Map matching if selected
        if str(parameters["map_match"])=="True" :
            feedback.pushInfo(self.tr("Map matching of PT lines on available network, it may take a while..."))
            transit.set_allow_map_match(True)  
            transit.map_match()
            feedback.setCurrentStep(i-1)
            feedback.pushInfo(" ")
        
        # Saving results
        feedback.pushInfo(self.tr("Saving results"))
        transit.save_to_disk()
        feedback.pushInfo(" ")
        feedback.setCurrentStep(i)
        
        project.close()
        
        return {"Output": "Traffic assignment successfully completed"}

    def name(self):
        return self.tr("Import GTFS")

    def displayName(self):
        return self.tr("Import GTFS")

    def group(self):
        return ("04-"+self.tr("Public transport"))

    def groupId(self):
        return ("04-"+self.tr("Public transport"))

    def shortHelpString(self):
        return self.tr("Add PT lines from a GTFS file to an existing aequilibrae project")

    def createInstance(self):
        return ImportGTFS()

    def tr(self, message):
        return trlt("ImportGTFS", message)

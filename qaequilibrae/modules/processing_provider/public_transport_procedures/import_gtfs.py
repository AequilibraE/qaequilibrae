import importlib.util as iutil
import sys

from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterString, QgsProcessingParameterBoolean

from qaequilibrae.i18n.translate import trlt


class ImportGTFS(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "project_path",
                self.tr("Project path"),
                behavior=QgsProcessingParameterFile.Folder,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "gtfs_file",
                self.tr("GTFS file"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="ZIP (*.zip)",
            )
        )
        self.addParameter(QgsProcessingParameterString("gtfs_agency", self.tr("Transit agency"), multiLine=False))
        self.addParameter(
            QgsProcessingParameterString(
                "gtfs_date",
                self.tr("Date to import (YYYY-MM-DD)"),
                defaultValue="1980-01-01",
                multiLine=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean("allow_map_match", self.tr("Map-match transit routes"), defaultValue=True)
        )

    def processAlgorithm(self, parameters, context, feedback):
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.project import Project
        from aequilibrae.transit import Transit

        i = 4 if parameters["allow_map_match"] else 3
        feedback = QgsProcessingMultiStepFeedback(i, feedback)
        feedback.pushInfo(self.tr("Opening project"))

        # Opening project
        project = Project()
        project.open(parameters["project_path"])
        feedback.setCurrentStep(1)
        feedback.pushInfo(" ")

        # Importing GTFS
        feedback.pushInfo(self.tr("Importing GTFS"))
        data = Transit(project)
        transit = data.new_gtfs_builder(agency=parameters["gtfs_agency"], file_path=parameters["gtfs_file"])
        transit.load_date(parameters["gtfs_date"])
        feedback.setCurrentStep(2)
        feedback.pushInfo(" ")

        # Map matching if selected
        if parameters["allow_map_match"]:
            feedback.pushInfo(self.tr("Map matching routes, it may take a while..."))
            transit.set_allow_map_match(True)
            transit.map_match()
            feedback.setCurrentStep(3)
            feedback.pushInfo(" ")

        # Saving results
        feedback.pushInfo(self.tr("Saving results"))
        transit.save_to_disk()
        feedback.pushInfo(" ")
        feedback.setCurrentStep(i)

        project.close()

        return {"Output": "Traffic assignment successfully completed"}

    def name(self):
        return "importgtfs"

    def displayName(self):
        return self.tr("Import GTFS")

    def group(self):
        return self.tr("4. Public Transport")

    def groupId(self):
        return "publictransport"

    def shortHelpString(self):
        return self.tr("Adds transit routes from a GTFS to an existing AequilibraE project.")

    def createInstance(self):
        return ImportGTFS()

    def tr(self, message):
        return trlt("ImportGTFS", message)

import importlib.util as iutil
import sys
import textwrap

from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterDefinition, QgsProcessingParameterString, QgsProcessingParameterNumber

from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.i18n.translate import trlt


class create_pt_graph(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "project_path",
                self.tr("Project path"),
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=standard_path(),
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "period_id",
                self.tr("Period id"),
                type=QgsProcessingParameterNumber.Integer, 
                minValue=0, 
                defaultValue=1
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "access_mode",
                self.tr("access mode"),
                multiLine=False,
                defaultValue="w"
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.transit import Transit
        from aequilibrae.project import Project


        feedback.pushInfo(self.tr("Opening project"))
        # Opening project
        project = Project()
        project.open(parameters["project_path"])
        data = Transit(project)
        
        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)

        feedback.pushInfo(self.tr("Creating graph"))
        # Creating graph
        graph = data.create_graph()
        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)
        
        # Connector matching
        project.network.build_graphs(period_id=parameters["period_id"])
        graph.create_line_geometry(method="connector project match", graph=parameters["access_mode"])
        
        feedback.pushInfo(self.tr("Saving graph"))
        # Saving graph
        data.save_graphs()

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)

        project.close()

        return {"Output": "PT graph successfully created"}

    def name(self):
        return self.tr("Create PT graph before PT assignment")

    def displayName(self):
        return self.tr("Create PT graph before PT assignment")

    def group(self):
        return ("04-"+self.tr("Public transport"))

    def groupId(self):
        return ("04-"+self.tr("Public transport"))

    def shortHelpString(self):
        return textwrap.dedent("\n".join([self.string_order(1)]))

    def createInstance(self):
        return create_pt_graph()

    def string_order(self, order):
        if order == 1:
            return self.tr("Create a PT graph.")

    def tr(self, message):
        return trlt("create_pt_graph", message)

import importlib.util as iutil
import sys

import yaml
from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile

from qaequilibrae.i18n.translate import trlt


class TransitAssignYAML(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "conf_file",
                self.tr("Configuration file (*.yaml)"),
                behavior=QgsProcessingParameterFile.File,
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae import Project
        from aequilibrae.matrix import AequilibraeMatrix
        from aequilibrae.paths import TransitAssignment, TransitClass
        from aequilibrae.project.database_connection import database_connection
        from aequilibrae.transit.transit_graph_builder import TransitGraphBuilder

        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        feedback.pushInfo(self.tr("Getting parameters from YAML"))

        pathfile = parameters["conf_file"]
        with open(pathfile, "r") as f:
            params = yaml.safe_load(f)

        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)

        # Opening project
        feedback.pushInfo(self.tr("Opening project"))

        project = Project()
        project.open(params["project_path"])
        project.network.build_graphs()

        # Load PT Graph
        pt_con = database_connection("transit")
        params["graph"]["public_transport_conn"] = pt_con

        graph_db = TransitGraphBuilder.from_db(**params["graph"])
        graph_db.create_graph()
        graph_db.create_line_geometry(method="connector project match", graph="c")

        graph = graph_db.to_transit_graph()

        # Load AequilibraE Matrix
        mat = AequilibraeMatrix()
        mat.load(params["matrix_path"])
        mat.computational_view()

        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        # Setting up assignment
        feedback.pushInfo(self.tr("Setting up assignment"))

        # Create the assignment class
        assigclass = TransitClass(name="pt", graph=graph, matrix=mat)
        assigclass.set_demand_matrix_core(params["matrix_core"])

        # Create PT Assignment object
        assig = TransitAssignment()
        assig.add_class(assigclass)
        assig.set_time_field(params["assignment"]["time_field"])
        assig.set_frequency_field(params["assignment"]["frequency"])
        assig.set_algorithm(params["assignment"]["algorithm"])

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)

        # Running assignment
        feedback.pushInfo(self.tr("Running assignment"))

        assig.execute()

        feedback.pushInfo(" ")
        feedback.setCurrentStep(4)

        # Saving outputs
        feedback.pushInfo(self.tr("Saving outputs"))

        assig.save_results(params["result_name"])

        feedback.pushInfo(" ")
        feedback.setCurrentStep(5)

        project.close()

        return {"Output": "Transit assignment successfully completed"}

    def name(self):
        return "ptassignfromyaml"

    def displayName(self):
        return self.tr("Transit assignment from file")

    def group(self):
        return self.tr("4. Public Transport")

    def groupId(self):
        return "publictransport"

    def shortHelpString(self):
        help_messages = [
            self.tr("Runs transit assignment using a YAML configuration file."),
            self.tr("Example of valid configuration is provided in the plugin documentation."),
        ]
        return "\n".join(help_messages)

    def createInstance(self):
        return TransitAssignYAML()

    def tr(self, message):
        return trlt("ptAssignYAML", message)

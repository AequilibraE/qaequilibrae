import importlib.util as iutil
import sys
import textwrap

from datetime import datetime as dt

from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterDefinition, QgsProcessingParameterBoolean

from qaequilibrae.i18n.translate import trlt


class ptAssignYAML(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "conf_file",
                self.tr("Configuration file (.yaml)"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="",
                defaultValue=None,
            )
        )
        
        advparameters = [
            QgsProcessingParameterBoolean(
            "datetime_to_resultname", 
            self.tr("Include current datetime to result name"), 
            defaultValue=True
            )
        ]
        
        for param in advparameters:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.paths import TransitAssignment, TransitClass
        from aequilibrae.transit import Transit
        from aequilibrae.project import Project
        from aequilibrae.matrix import AequilibraeMatrix
        from aequilibrae.project.database_connection import database_connection
        from aequilibrae.transit.transit_graph_builder import TransitGraphBuilder
        import yaml

        feedback.pushInfo(self.tr("Getting parameters from YAML"))
        pathfile = parameters["conf_file"]
        with open(pathfile, "r") as f:
            params = yaml.safe_load(f)
        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)

        feedback.pushInfo(self.tr("Opening project"))
        # Opening project
        project = Project()
        project.open(params["project"])
        data = Transit(project)

        pt_con = database_connection("transit")
        graph = TransitGraphBuilder.from_db(pt_con, int(params["assignment"]["period_id"]))
        
        transit_graph = graph.to_transit_graph()

        # Creating traffic classes
        transit_classes = []
        feedback.pushInfo(self.tr("{} traffic classes have been found").format(len(params["transit_classes"])))
        select_links = "select_links" in params and params["select_links"]
        if select_links:
            selection_dict = {}
            for selections in params["select_links"]:
                for name in selections:
                    link_list = ''
                    for text in selections[name]:
                        link_list = link_list + ',' + text
                    link_list = ('[' + link_list[1:] + ']')
                    link_list=eval(link_list)
                    selection_dict[name] = link_list
        
        for classes in params["transit_classes"]:
            for transit in classes:

                # Getting matrix
                demand = AequilibraeMatrix()
                demand.load(classes[transit]["matrix_path"])
                demand.computational_view([classes[transit]["matrix_core"]])

                # Getting graph
                if str(classes[transit]["blocked_centroid_flows"])=="True":
                    transit_graph.set_blocked_centroid_flows(True)
                else:
                    transit_graph.set_blocked_centroid_flows(False)

                if "skims" in classes[transit] and classes[transit]["skims"]:
                    skims = [sk.strip() for sk in classes[transit]["skims"].split(",")]
                    transit_graph.set_skimming(skims)

                # Setting class
                assigclass = TransitClass(name=transit, graph=transit_graph, matrix=demand, matrix_core= classes[transit]["matrix_core"])

                # Adding class
                feedback.pushInfo(f"\t- {transit} ' ' {str(classes[transit])}")

                transit_classes.append(assigclass)
        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        # Setting up assignment
        feedback.pushInfo(self.tr("Setting up assignment"))

        assig = TransitAssignment()
        assig.set_classes(transit_classes)
        assig.set_frequency_field("freq")
        assig.set_time_field("trav_time")

        assig.set_algorithm("os")

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)

        # Running assignment
        feedback.pushInfo(self.tr("Running assignment"))
        feedback.pushInfo(str(parameters["assignment"]))
        assig.execute()
        feedback.pushInfo(" ")
        feedback.setCurrentStep(4)

        # Saving outputs
        feedback.pushInfo(self.tr("Saving outputs"))
        if str(parameters["datetime_to_resultname"])=="True":
            params["result_name"]=(params["result_name"]+dt.now().strftime("_%Y-%m-%d_%Hh%M"))
        assig.save_results(params["result_name"])

        feedback.pushInfo(" ")
        feedback.setCurrentStep(5)

        project.close()

        return {"Output": "PT assignment successfully completed"}

    def name(self):
        return self.tr("PT assignment from file")

    def displayName(self):
        return self.tr("PT assignment from file")

    def group(self):
        return ("04-"+self.tr("Public transport"))

    def groupId(self):
        return ("04-"+self.tr("Public transport"))

    def shortHelpString(self):
        return textwrap.dedent("\n".join([self.string_order(1), self.string_order(2), self.string_order(3)]))

    def createInstance(self):
        return ptAssignYAML()

    def string_order(self, order):
        if order == 1:
            return self.tr("Run a pt assignment using a YAML configuration file.")
        elif order == 2:
            return self.tr("Example of valid configuration file:")
        elif order == 3:
            return textwrap.dedent("""\
                project: D:/AequilibraE/Project/
                
                result_name: sce_from_yaml
                
                transit_classes:
                    - student:
                        matrix_path: D:/AequilibraE/Project/matrices/demand.aem
                        matrix_core: student_pt
                        blocked_centroid_flows: True
                        skims: travel_time, distance
                    - worker:
                        matrix_path: D:/AequilibraE/Project/matrices/demand.aem
                        matrix_core: worker_pt
                        blocked_centroid_flows: True
                        
                assignment:
                    period_id: 1
                """)

    def tr(self, message):
        return trlt("ptAssignYAML", message)

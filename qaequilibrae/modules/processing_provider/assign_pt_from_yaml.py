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
        
        advparams = [
            QgsProcessingParameterBoolean(
            "datetime_to_resultname", 
            self.tr("Include current datetime to result name"), 
            defaultValue=True
            )
        ]
        
        for param in advparams:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.paths import TrafficAssignment, TrafficClass
        from aequilibrae.project import Project
        from aequilibrae.matrix import AequilibraeMatrix
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

        # Creating graph
        graph = data.create_graph()
        
        # Connector matching
        project.network.build_graphs()
        graph.create_line_geometry(method="connector project match", graph="w")

        # Creating traffic classes
        transit_classes = []
        feedback.pushInfo(self.tr("{} traffic classes have been found").format(len(params["transit_classes"])))
        select_links = "select_links" in params and params["select_links"]
        if select_links:
            selection_dict={}
            for selections in params["select_links"]:
                for name, links_list in selections:
                    exec(f'selection_dict[{name}]= {links_list}')
        
        for classes in params["transit_classes"]:
            for transit in classes:

                # Getting matrix
                demand = AequilibraeMatrix()
                demand.load(classes[transit]["matrix_path"])
                demand.computational_view([classes[transit]["matrix_core"]])

                # Getting graph
                if str(classes[transit]["blocked_centroid_flows"])=="True":
                    graph.set_blocked_centroid_flows(True)
                else:
                    graph.set_blocked_centroid_flows(False)

                if "skims" in classes[transit] and classes[transit]["skims"]:
                    skims = [sk.strip() for sk in classes[transit]["skims"].split(",")]
                    graph.set_skimming(skims)

                # Setting class
                transit_graph = graph.to_transit_graph()
                assigclass = TransitClass(name=transit, graph=transit_graph, matrix=demand, matrix_core= classes[transit]["matrix_core"])

                # Adding class
                feedback.pushInfo(f"\t- {transit} ' ' {str(classes[transit])}")

                transit_classes.append(assigclass)
        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        # Setting up assignment
        feedback.pushInfo(self.tr("Setting up assignment"))
        feedback.pushInfo(str(params["assignment"]))

        assig = TransitAssignment()
        assig.set_classes(transit_classes)
        assig.set_frequency_field(params["assignment"]["freq_field"])
        assig.set_time_field(params["assignment"]["time_field"])

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
        feedback.pushInfo(str(assig.report()))
        if str(parameters["datetime_to_resultname"])=="True":
            assig.save_results(params["result_name"]+dt.now().strftime("_%Y-%m-%d_%Hh%M"))
        else:
            assig.save_results(params["result_name"])
        assig.save_skims(params["result_name"], which_ones="all", format="aem")

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
                    - truck:
                        matrix_path: D:/AequilibraE/Project/matrices/demand.aem
                        matrix_core: truck_pt
                        blocked_centroid_flows: True
                        
                assignment:
                    time_field : trav_time
                    freq_field : freq
                    algorithl: os
                """)

    def tr(self, message):
        return trlt("ptAssignYAML", message)

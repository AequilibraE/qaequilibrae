import importlib.util as iutil
import sys

import yaml
from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile

from qaequilibrae.i18n.translate import trlt


class TrafficAssignYAML(QgsProcessingAlgorithm):

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
        from aequilibrae.paths import TrafficAssignment, TrafficClass

        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
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

        # Creating graph
        project.network.build_graphs()

        # Creating traffic classes
        traffic_classes = []
        feedback.pushInfo(self.tr("{} traffic classes have been found").format(len(params["traffic_classes"])))
        select_links = True if "select_links" in params and params["select_links"] is not None else False
        if select_links:
            selection_dict = {}
            for selections in params["select_links"]:
                for name, pairs in selections.items():
                    selection_dict[name] = [tuple(p) for p in pairs]

        for classes in params["traffic_classes"]:
            for traffic in classes:

                # Getting matrix
                demand = AequilibraeMatrix()
                demand.load(classes[traffic]["matrix_path"])
                demand.computational_view([classes[traffic]["matrix_core"]])

                # Getting graph
                graph = project.network.graphs[classes[traffic]["network_mode"]]
                graph.set_graph(params["assignment"]["time_field"])
                graph.set_blocked_centroid_flows(classes[traffic]["blocked_centroid_flows"])

                if classes[traffic]["skims"] is not None:
                    skims = [sk.strip() for sk in classes[traffic]["skims"].split(",")]
                    graph.set_skimming(skims)

                # Setting class
                assigclass = TrafficClass(name=traffic, graph=graph, matrix=demand)
                assigclass.set_pce(classes[traffic]["pce"])

                if "fixed_cost" in classes[traffic] and classes[traffic]["fixed_cost"] is not None:
                    if isinstance(classes[traffic]["vot"], (int, float)):
                        assigclass.set_fixed_cost(classes[traffic]["fixed_cost"])
                        assigclass.set_vot(classes[traffic]["vot"])
                    else:
                        sys.exit("Error: fixed_cost must come with a correct value of time")

                # Adding select links analysis
                if select_links:
                    assigclass.set_select_links(selection_dict)

                # Adding class
                traffic_classes.append(assigclass)
                feedback.pushInfo(f"\t- {traffic} ' ' {str(classes[traffic])}")

        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        # Setting up assignment
        feedback.pushInfo(self.tr("Setting up assignment"))
        feedback.pushInfo(str(params["assignment"]))

        assig = TrafficAssignment()
        assig.set_classes(traffic_classes)
        assig.set_vdf(params["assignment"]["vdf"])
        assig.set_vdf_parameters({"alpha": params["assignment"]["alpha"], "beta": params["assignment"]["beta"]})
        assig.set_capacity_field(params["assignment"]["capacity_field"])
        assig.set_time_field(params["assignment"]["time_field"])

        assig.set_algorithm(params["assignment"]["algorithm"])
        assig.max_iter = params["assignment"]["max_iter"]
        assig.rgap_target = params["assignment"]["rgap"]

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)

        # Running assignment
        feedback.pushInfo(self.tr("Running assignment"))
        feedback.pushInfo(" ")
        feedback.setCurrentStep(4)
        assig.execute()

        # Saving outputs
        feedback.pushInfo(self.tr("Saving outputs"))
        assig.save_results(params["result_name"])
        assig.save_skims(params["result_name"], which_ones="all", format="omx")

        if select_links:
            assig.procedure_id += "SLA"
            sl_name = f"{params["result_name"]}_select_link_analysis"
            assig.save_select_link_results(sl_name)
        feedback.pushInfo(" ")
        feedback.setCurrentStep(5)

        project.close()

        return {"Output": "Traffic assignment successfully completed"}

    def name(self):
        return "assignmentfromyaml"

    def displayName(self):
        return self.tr("Traffic assignment from file")

    def group(self):
        return self.tr("3. Paths and assignment")

    def groupId(self):
        return "pathsandassignment"

    def shortHelpString(self):
        help_messages = [
            self.tr("Runs traffic assignment using a YAML configuration file."),
            self.tr("Example of valid configuration is provided in the plugin documentation."),
        ]
        return "\n".join(help_messages)

    def createInstance(self):
        return TrafficAssignYAML()

    def tr(self, message):
        return trlt("TrafficAssignYAML", message)

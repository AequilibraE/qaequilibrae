import importlib.util as iutil

from qgis.core import QgsProcessingException

from ..project import open_project
from ..project_algorithm import ProjectAlgorithm


class NetworkSimplifier(ProjectAlgorithm):
    algorithm_name = "Network simplifier"
    display_name = "Network simplifier"
    translate_algorithm_name = True
    group_name = "Model building"
    group_id = "model_building"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.project_folder(parameters, context)

        if iutil.find_spec("aequilibrae") is None:
            raise QgsProcessingException(self.tr("AequilibraE module not found"))

        from aequilibrae.project.tools.network_simplifier import NetworkSimplifier

        try:
            with open_project(project_folder) as project:
                return self._simplify(project, project_folder, feedback, NetworkSimplifier)
        except Exception as error:
            raise QgsProcessingException(
                self.tr(f"{project_folder} does not contain an AequilibraE model: {error}")
            ) from error

    def _simplify(self, project, project_folder, feedback, network_simplifier):
        feedback.pushInfo("Checking centroids")
        nodes = project.network.nodes
        centroid_count = nodes.data.query("is_centroid == 1").shape[0]
        feedback.pushInfo(str(centroid_count))

        if centroid_count == 0:
            feedback.pushInfo("Creating arbitrary centroid")
            arbitrary_node = nodes.data["node_id"][0]
            temporary_centroid = nodes.get(arbitrary_node)
            temporary_centroid.is_centroid = 1
            temporary_centroid.save()

        # TODO: Check whether mode "c" is appropriate for every project.
        mode = "c"

        feedback.pushInfo("Setting graph for computation")
        network = project.network
        network.build_graphs(modes=[mode])

        graph = network.graphs[mode]
        graph.set_graph("distance")
        graph.set_skimming("distance")
        graph.set_blocked_centroid_flows(False)

        feedback.pushInfo(str(graph.network))

        if centroid_count == 0:
            feedback.pushInfo("Revert nodes as centroids")
            temporary_centroid.is_centroid = 0
            temporary_centroid.save()

        links_before = project.network.links.data.shape[0]
        nodes_before = project.network.nodes.data.shape[0]

        simplifier = network_simplifier()
        feedback.pushInfo("Simplify network")
        simplifier.simplify(graph)
        feedback.pushInfo("Saving network")
        simplifier.rebuild_network()

        links_after = project.network.links.data.shape[0]
        nodes_after = project.network.nodes.data.shape[0]

        feedback.pushInfo(f"Project closed in {project_folder}")

        summary = f"This project initially had {links_before} links and {nodes_before} nodes"
        summary += f"\nNow it has {links_after} links and {nodes_after} nodes."
        feedback.pushInfo(summary)

        return {"Output": "Ok."}

    def shortHelpString(self):
        return self.tr("Simplifies the network by merging links and removing intermediate nodes.")

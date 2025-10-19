import importlib.util as iutil

from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFile, QgsProcessingException

from qaequilibrae.i18n.translate import trlt


class NetworkSimplifier(QgsProcessingAlgorithm):

    PROJECT_FOLDER = "PROJECT_FOLDER"

    def initAlgorithm(self, config=None):
        # 1. Folder containing an AequilibraE project
        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECT_FOLDER, self.tr("AequilibraE Project Folder"), behavior=QgsProcessingParameterFile.Folder
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.parameterAsFile(parameters, self.PROJECT_FOLDER, context)

        # Checks if we have access to AequilibraE library
        if iutil.find_spec("aequilibrae") is None:
            raise QgsProcessingException(self.tr("AequilibraE module not found"))

        from aequilibrae.project import Project
        from aequilibrae.project.tools.network_simplifier import NetworkSimplifier

        # Check if folder contains AequilibraE project
        try:
            project = Project()
            project.open(project_folder)
        except Exception as e:
            raise QgsProcessingException(self.tr(f"{project_folder} does not contain an AequilibraE model: {e}"))

        # Check if centroids exists, otherwise create a centroid
        feedback.pushInfo("Checking centroids")
        nodes = project.network.nodes
        centroid_count = nodes.data.query("is_centroid == 1").shape[0]
        feedback.pushInfo(str(centroid_count))

        if centroid_count == 0:
            feedback.pushInfo("Creating arbitrary centroid")
            arbitrary_node = nodes.data["node_id"][0]
            nd = nodes.get(arbitrary_node)
            nd.is_centroid = 1
            nd.save()

        # TODO: I don't know if its a good idea setting up a mode here.
        mode = "c"

        # Let's set the graph for computation
        feedback.pushInfo("Setting graph for computation")
        network = project.network
        network.build_graphs(modes=[mode])

        graph = network.graphs[mode]
        graph.set_graph("distance")
        graph.set_skimming("distance")
        graph.set_blocked_centroid_flows(False)

        feedback.pushInfo(str(graph.network))

        # Let's revert to setting up that node as centroid in case we had to do it
        if centroid_count == 0:
            feedback.pushInfo("Revert nodes as centroids")
            nd.is_centroid = 0
            nd.save()

        links_before = project.network.links.data.shape[0]
        nodes_before = project.network.nodes.data.shape[0]

        net = NetworkSimplifier()
        feedback.pushInfo("Simplify network")
        net.simplify(graph)
        feedback.pushInfo("Saving network")
        net.rebuild_network()

        links_after = project.network.links.data.shape[0]
        nodes_after = project.network.nodes.data.shape[0]

        project.close()
        feedback.pushInfo(f"Project closed in {project_folder}")

        exp = "This project initially had {} links and {} nodes".format(links_before, nodes_before)
        exp = exp + "\nNow it has {} links and {} nodes.".format(links_after, nodes_after)
        feedback.pushInfo(exp)

        return {"Output": "Ok."}

    def name(self):
        return self.tr("Network simplifier")

    def displayName(self) -> str:
        return self.tr("Network simplifier")

    def group(self) -> str:
        return self.tr("Model building")

    def groupId(self) -> str:
        return "model_building"

    def shortHelpString(self):
        help_messages = [
            self.tr("This tool simplifies the network, merging short links into longer ones or"),
            self.tr("turning links into nodes, and saving theses changes into the project."),
        ]
        return "\n".join(help_messages)

    def createInstance(self):
        return NetworkSimplifier()

    def tr(self, message):
        return trlt("NetworkSimplifier", message)

import importlib.util as iutil
import sys

from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterString
from qgis.core import QgsProcessingParameterFile, QgsProcessingException

from qaequilibrae.i18n.translate import trlt


class CollapseLinks(QgsProcessingAlgorithm):

    PROJECT_FOLDER = "PROJECT_FOLDER"
    LINK_IDS = "LINK_IDS"

    def initAlgorithm(self, config=None):
        # 1. Folder containing an AequilibraE project
        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECT_FOLDER, self.tr("AequilibraE Project Folder"), behavior=QgsProcessingParameterFile.Folder
            )
        )

        # 2. Way of selecting one or more LINK_IDS
        self.addParameter(
            QgsProcessingParameterString(self.LINK_IDS, self.tr("Link IDs (comma-separated)"), defaultValue="")
        )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.parameterAsFile(parameters, self.PROJECT_FOLDER, context)
        link_ids_raw = self.parameterAsString(parameters, self.LINK_IDS, context)

        # Checks if we have access to AequilibraE library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.project import Project
        from aequilibrae.project.tools.network_simplifier import NetworkSimplifier

        # Check if folder contains AequilibraE project
        try:
            project = Project()
            project.open(project_folder)
        except Exception as e:
            raise QgsProcessingException(self.tr(f"{project_folder} does not contain an AeqilibraE model: {e}"))

        # Parse LINK_IDS
        try:
            link_ids = [int(n.strip()) for n in link_ids_raw.split(",") if n.strip()]
        except Exception as e:
            raise QgsProcessingException(self.tr(f"Error parsing link IDs: {e}"))

        net = NetworkSimplifier()

        feedback.pushInfo("Collapsing links into nodes")
        net.collapse_links_into_nodes(link_ids)

        feedback.pushInfo("Saving network")
        net.rebuild_network()

        project.close()
        feedback.pushInfo(f"Project closed in {project_folder}")

        return {"SELECTED_NODE_COUNT": len(link_ids), "SELECTED_LINK_IDS": link_ids}

    def name(self):
        return self.tr("Collapse links")

    def displayName(self) -> str:
        return self.tr("Collapse links")

    def group(self) -> str:
        return self.tr("Model building")

    def groupId(self) -> str:
        return "model_building"

    def shortHelpString(self):
        return self.tr("This tool collapses links into nodes, adjusting the network in the neighborhood.")

    def createInstance(self):
        return CollapseLinks()

    def tr(self, message):
        return trlt("CollapseLinks", message)

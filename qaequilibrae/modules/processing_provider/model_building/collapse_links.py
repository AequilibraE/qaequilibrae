from qgis.core import QgsProcessingException, QgsProcessingParameterString

from ..project import open_project
from ..project_algorithm import ProjectAlgorithm


class CollapseLinks(ProjectAlgorithm):
    algorithm_name = "Collapse links"
    display_name = "Collapse links"
    translate_algorithm_name = True
    group_name = "Model building"
    group_id = "model_building"

    LINK_IDS = "LINK_IDS"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(
            QgsProcessingParameterString(self.LINK_IDS, self.tr("Link IDs (comma-separated)"), defaultValue="")
        )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.project_folder(parameters, context)
        link_ids_raw = self.parameterAsString(parameters, self.LINK_IDS, context)

        try:
            link_ids = [int(n.strip()) for n in link_ids_raw.split(",") if n.strip()]
        except Exception as e:
            raise QgsProcessingException(self.tr(f"Error parsing link IDs: {e}")) from e

        try:
            with open_project(project_folder):
                from aequilibrae.project.tools.network_simplifier import NetworkSimplifier

                net = NetworkSimplifier()
                feedback.pushInfo("Collapsing links into nodes")
                net.collapse_links_into_nodes(link_ids)

                feedback.pushInfo("Saving network")
                net.rebuild_network()
        except Exception as e:
            raise QgsProcessingException(self.tr(f"{project_folder} does not contain an AeqilibraE model: {e}")) from e

        feedback.pushInfo(f"Project closed in {project_folder}")

        return {"SELECTED_NODE_COUNT": len(link_ids), "SELECTED_LINK_IDS": link_ids}

    def shortHelpString(self):
        return self.tr("Collapses links into nodes and updates the surrounding network.")

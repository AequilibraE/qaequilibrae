"""Create centroids and connect them to a project network."""

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingOutputNumber,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from qaequilibrae.modules.common_tools import polygon_from_radius

from ..project import borrow_project
from ..project_algorithm import ProjectAlgorithm


def add_zone_centroids(project, feedback):
    zones = project.zoning.all_zones()
    nodes = project.network.nodes
    nodes.refresh()
    existing = {int(row.node_id): int(row.is_centroid) for row in nodes.data.itertuples()}
    for identifier in zones:
        if identifier in existing and existing[identifier] != 1:
            raise QgsProcessingException(f"Zone ID {identifier} belongs to a regular node")
    added = 0
    for identifier, zone in zones.items():
        if feedback.isCanceled():
            break
        if identifier not in existing:
            zone.add_centroid(None)
            added += 1
    nodes.refresh()
    return added


class AddCentroidsFromZones(ProjectAlgorithm):
    algorithm_name = "add_centroids_from_zones"
    display_name = "Add centroids from zones"
    group_name = "Model building"
    group_id = "model_building"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addOutput(QgsProcessingOutputNumber("ADDED", self.tr("Centroids added")))

    def processAlgorithm(self, parameters, context, feedback):
        with borrow_project(self.project_folder(parameters, context)) as project:
            added = add_zone_centroids(project, feedback)
        return {"ADDED": added}

    def shortHelpString(self):
        return self.tr("Creates a centroid for each project zone without one. Existing centroids are retained.")


class AddCentroidConnectors(ProjectAlgorithm):
    algorithm_name = "addcentroidconnector"
    display_name = "Add centroid connectors"
    group_name = "Model building"
    group_id = "model_building"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(QgsProcessingParameterString("MODES", self.tr("Mode IDs (empty for all)"), optional=True))
        self.addParameter(
            QgsProcessingParameterString("LINK_TYPES", self.tr("Link type IDs (empty for all)"), optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "CONNECTORS",
                self.tr("Connectors per centroid and mode"),
                type=Qgis.ProcessingNumberParameterType.Integer,
                minValue=1,
                defaultValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "RADIUS", self.tr("Initial search radius (meters)"), minValue=1, defaultValue=3000
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean("FROM_ZONES", self.tr("Create missing centroids from project zones"), False)
        )
        self.addOutput(QgsProcessingOutputNumber("ADDED", self.tr("Links added")))

    def processAlgorithm(self, parameters, context, feedback):
        with borrow_project(self.project_folder(parameters, context)) as project:
            modes = self.parameterAsString(parameters, "MODES", context).strip()
            link_types = self.parameterAsString(parameters, "LINK_TYPES", context).strip()
            available_modes = project.network.modes.all_modes()
            available_types = project.network.link_types.all_types()
            if set(modes) - set(available_modes) or set(link_types) - set(available_types):
                raise QgsProcessingException(self.tr("Unknown mode or link type ID"))
            modes = modes or "".join(available_modes)
            link_types = link_types or "".join(available_types)
            if self.parameterAsBool(parameters, "FROM_ZONES", context):
                add_zone_centroids(project, feedback)
            nodes = project.network.nodes
            nodes.refresh()
            identifiers = nodes.data.loc[nodes.data.is_centroid == 1, "node_id"].tolist()
            before = project.network.count_links()
            for index, identifier in enumerate(identifiers):
                if feedback.isCanceled():
                    break
                node = nodes.get(int(identifier))
                area = polygon_from_radius(node.geometry, self.parameterAsDouble(parameters, "RADIUS", context))
                for mode in dict.fromkeys(modes):
                    if feedback.isCanceled():
                        break
                    node.connect_mode(
                        mode_id=mode,
                        link_types=link_types,
                        area=area,
                        connectors=self.parameterAsInt(parameters, "CONNECTORS", context),
                    )
                feedback.setProgress(100 * (index + 1) / len(identifiers))
            project.network.links.refresh()
            nodes.refresh()
            added = project.network.count_links() - before
        return {"ADDED": added}

    def shortHelpString(self):
        return self.tr(
            "Connects project centroids to eligible network nodes. The search radius is in meters. "
            "AequilibraE expands the search when no eligible node exists in the initial area."
        )

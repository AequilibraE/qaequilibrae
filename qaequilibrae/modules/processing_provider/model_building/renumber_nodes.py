"""Match centroid points to existing nodes before changing their identifiers."""

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingOutputNumber,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
)

from ..geometry_io.common import source_rows
from ..project import borrow_project
from ..project_algorithm import ProjectAlgorithm


def point_key(point):
    if point is None or point.geom_type != "Point" or point.is_empty:
        raise QgsProcessingException("Each centroid must have a point geometry")
    return round(point.x, 8), round(point.y, 8)


class RenumberNodesFromLayer(ProjectAlgorithm):
    algorithm_name = "renumbernodes"
    display_name = "Add or renumber centroids from layer"
    group_name = "Model building"
    group_id = "model_building"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(
            QgsProcessingParameterFeatureSource("INPUT", self.tr("Centroids"), [Qgis.ProcessingSourceType.VectorPoint])
        )
        self.addParameter(
            QgsProcessingParameterField(
                "NODE_ID",
                self.tr("Centroid ID field"),
                parentLayerParameterName="INPUT",
                type=Qgis.ProcessingFieldParameterDataType.Numeric,
            )
        )
        for name in ("ADDED", "RENUMBERED", "MATCHED"):
            self.addOutput(QgsProcessingOutputNumber(name, self.tr(name.title() + " nodes")))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, "INPUT", context)
        if source is None:
            raise QgsProcessingException(self.tr("The centroid layer could not be loaded"))
        field = self.parameterAsString(parameters, "NODE_ID", context).lower()
        rows = source_rows(source)
        requested = {}
        points = set()
        for row in rows:
            value = row.get(field)
            try:
                if value is None:
                    raise ValueError
                identifier = int(value)
                if identifier <= 0 or identifier > 9223372036854775807 or value != identifier:
                    raise ValueError
            except (TypeError, ValueError, OverflowError) as error:
                raise QgsProcessingException(self.tr("Centroid IDs must be positive integers")) from error
            key = point_key(row["geometry"])
            if identifier in requested or key in points:
                raise QgsProcessingException(self.tr("Centroid IDs and locations must be unique"))
            requested[identifier] = (key, row["geometry"])
            points.add(key)
        with borrow_project(self.project_folder(parameters, context)) as project:
            nodes = project.network.nodes
            nodes.refresh()
            locations = {}
            occupied = set()
            for row in nodes.data.itertuples():
                locations.setdefault(point_key(row.geometry), []).append(int(row.node_id))
                occupied.add(int(row.node_id))
            matches = {}
            for identifier, (key, _) in requested.items():
                candidates = locations.get(key, [])
                if len(candidates) > 1:
                    raise QgsProcessingException(self.tr(f"Multiple nodes match centroid {identifier}"))
                if candidates:
                    matches[identifier] = candidates[0]
            moving = {old for new, old in matches.items() if new != old}
            for identifier in requested:
                if identifier in occupied and matches.get(identifier) != identifier and identifier not in moving:
                    raise QgsProcessingException(self.tr(f"Node ID {identifier} is already in use"))
            if feedback.isCanceled():
                return {}
            # Move all matched nodes aside first, so swaps cannot collide with an existing ID.
            temporary = max(occupied | set(requested) | {0}) + 1
            if moving and temporary + len(moving) - 1 > 9223372036854775807:
                raise QgsProcessingException(self.tr("Node IDs leave no space for temporary renumbering"))
            records = {}
            for identifier, old in matches.items():
                node = nodes.get(old)
                node.is_centroid = 1
                node.save()
                if old != identifier:
                    node.renumber(temporary)
                    temporary += 1
                records[identifier] = node
            # Complete the ID changes together; cancellation must not leave temporary IDs behind.
            for identifier, node in records.items():
                if node.node_id != identifier:
                    node.renumber(identifier)
            for identifier, (_, geometry) in requested.items():
                if identifier not in matches:
                    node = nodes.new_centroid(identifier)
                    node.geometry = geometry
                    node.save()
            nodes.refresh()
            project.network.links.refresh()
        return {"ADDED": len(requested) - len(matches), "RENUMBERED": len(moving), "MATCHED": len(matches)}

    def shortHelpString(self):
        return self.tr(
            "Matches points in EPSG:4326 rounded to eight decimal places. Matched nodes become centroids "
            "with the requested IDs; unmatched points create centroids. Duplicate locations and occupied IDs are rejected."
        )

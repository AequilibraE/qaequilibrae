"""Algorithms that append geometry records to an AequilibraE project."""

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingOutputNumber,
    QgsProcessingParameterFeatureSource,
)

from ..project_algorithm import ProjectAlgorithm
from .common import record_data_fields, source_rows
from .project import open_project


class AddProjectLayer(ProjectAlgorithm):
    """Base class for adding vector features to a project table."""

    INPUT = "INPUT"
    group_name = "Geometry IO"
    group_id = "geometry_io"
    table_name = ""
    id_field = ""
    geometry_source_type = Qgis.ProcessingSourceType.VectorLine
    display_name = ""
    algorithm_name = ""

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addOutput(QgsProcessingOutputNumber("ADDED", self.tr("Features added")))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr(self.display_name + " input"),
                types=[self.geometry_source_type],
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.tr("The input layer could not be loaded"))
        rows = source_rows(source)
        project_folder = self.project_folder(parameters, context)
        with open_project(project_folder) as project:
            if self.table_name == "zones":
                with project.db_connection as connection:
                    has_zoning = connection.execute(
                        "select exists(select 1 from sqlite_master where type='table' and name='zones')"
                    ).fetchone()[0]
                if not has_zoning:
                    # Older projects can be created without a zoning table. The API
                    # creates it lazily when the first zoning record is added.
                    project.zoning.create_zoning_layer()
            added = 0
            table = project.zoning if self.table_name == "zones" else getattr(project.network, self.table_name)
            ignored_fields = {"geometry", "ogc_fid"}
            if self.id_field:
                ignored_fields.add(self.id_field)
            if self.table_name == "links":
                ignored_fields.update({"a_node", "b_node", "distance"})
            elif self.table_name == "nodes":
                ignored_fields.update({"modes", "link_types"})
            elif self.table_name == "zones":
                ignored_fields.add("area")
            for row in rows:
                if feedback.isCanceled():
                    break
                identifier = row.get(self.id_field) if self.id_field else None
                if self.id_field and identifier is None:
                    raise QgsProcessingException(self.tr(f"The input is missing {self.id_field}"))
                record = self._new_record(project, int(identifier) if identifier is not None else None)
                if self.table_name == "nodes" and row.get("is_centroid") is None:
                    record.is_centroid = 0
                for field, value in row.items():
                    if field in ignored_fields or value is None:
                        continue
                    if field in record_data_fields(record, table):
                        setattr(record, field, value)
                if row["geometry"] is None:
                    raise QgsProcessingException(self.tr(f"Feature {identifier} has no geometry"))
                record.geometry = row["geometry"]
                record.save()
                added += 1
        feedback.pushInfo(self.tr(f"Added {added} {self.table_name}"))
        return {"ADDED": added}

    def _new_record(self, project, identifier):
        table = project.zoning if self.table_name == "zones" else getattr(project.network, self.table_name)
        if self.table_name == "nodes":
            return table.new_centroid(identifier)
        if self.table_name == "zones":
            return table.new(identifier)
        return table.new()

    def name(self):
        return self.algorithm_name

    def displayName(self):
        return self.tr(self.display_name)

    def shortHelpString(self):
        message = f"Adds {self.table_name} to an AequilibraE project."
        if self.table_name == "links":
            message += " Link IDs are assigned by the project."
        return self.tr(message)

    def createInstance(self):
        return type(self)()

class AddLinks(AddProjectLayer):
    table_name = "links"
    id_field = None
    geometry_source_type = Qgis.ProcessingSourceType.VectorLine
    display_name = "Add links"
    algorithm_name = "add_links"


class AddNodes(AddProjectLayer):
    table_name = "nodes"
    id_field = "node_id"
    geometry_source_type = Qgis.ProcessingSourceType.VectorPoint
    display_name = "Add nodes"
    algorithm_name = "add_nodes"


class AddZones(AddProjectLayer):
    table_name = "zones"
    id_field = "zone_id"
    geometry_source_type = Qgis.ProcessingSourceType.VectorPolygon
    display_name = "Add zones"
    algorithm_name = "add_zones"

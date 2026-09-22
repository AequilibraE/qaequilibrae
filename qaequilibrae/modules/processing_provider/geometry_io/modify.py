"""Algorithms that update existing project geometry from vector layers."""

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingOutputNumber,
    QgsProcessingParameterFeatureSource,
)

from ..project_algorithm import ProjectAlgorithm
from .common import record_data_fields, source_rows
from .project import open_project


class ModifyProjectLayer(ProjectAlgorithm):
    """Update existing records, matched by the table's immutable identifier."""

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
        self.addOutput(QgsProcessingOutputNumber("UPDATED", self.tr("Features updated")))
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
            table = project.zoning if self.table_name == "zones" else getattr(project.network, self.table_name)
            updated = 0
            ignored_fields = {self.id_field, "geometry", "ogc_fid"}
            if self.table_name == "nodes":
                ignored_fields.update({"modes", "link_types"})
            elif self.table_name == "links":
                ignored_fields.add("distance")
            elif self.table_name == "zones":
                ignored_fields.add("area")
            for row in rows:
                if feedback.isCanceled():
                    break
                identifier = row.get(self.id_field)
                if identifier is None:
                    raise QgsProcessingException(self.tr(f"The input is missing {self.id_field}"))
                try:
                    record = table.get(int(identifier))
                except (TypeError, ValueError) as error:
                    raise QgsProcessingException(self.tr(f"Could not find {self.id_field} {identifier}")) from error
                for field, value in row.items():
                    if field in ignored_fields:
                        continue
                    if field in record_data_fields(record, table):
                        setattr(record, field, value)
                if row["geometry"] is not None:
                    record.geometry = row["geometry"]
                record.save()
                updated += 1
        feedback.pushInfo(self.tr(f"Updated {updated} {self.table_name}"))
        return {"UPDATED": updated}

    def name(self):
        return self.algorithm_name

    def displayName(self):
        return self.tr(self.display_name)

    def shortHelpString(self):
        return self.tr(f"Updates existing {self.table_name} using {self.id_field} as the key.")

    def createInstance(self):
        return type(self)()

class ModifyLinks(ModifyProjectLayer):
    table_name = "links"
    id_field = "link_id"
    geometry_source_type = Qgis.ProcessingSourceType.VectorLine
    display_name = "Modify links"
    algorithm_name = "modify_links"


class ModifyNodes(ModifyProjectLayer):
    table_name = "nodes"
    id_field = "node_id"
    geometry_source_type = Qgis.ProcessingSourceType.VectorPoint
    display_name = "Modify nodes"
    algorithm_name = "modify_nodes"


class ModifyZones(ModifyProjectLayer):
    table_name = "zones"
    id_field = "zone_id"
    geometry_source_type = Qgis.ProcessingSourceType.VectorPolygon
    display_name = "Modify zones"
    algorithm_name = "modify_zones"

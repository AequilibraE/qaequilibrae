"""Algorithms that export project geometry to Processing sinks."""

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
)

from ..project_algorithm import ProjectAlgorithm
from .common import add_dataframe_to_sink, fields_from_dataframe
from ..project import open_project


class ExtractProjectLayer(ProjectAlgorithm):
    """Base class for exporting one project table as a vector layer."""

    algorithm_name = ""
    display_name = ""
    group_name = "Geometry IO"
    group_id = "geometry_io"

    OUTPUT = "OUTPUT"
    table_name = ""
    geometry_type = Qgis.ProcessingSourceType.VectorLine
    sink_geometry_type = Qgis.WkbType.LineString

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr(self.display_name), type=self.geometry_type)
        )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.project_folder(parameters, context)
        with open_project(project_folder) as project:
            dataframe = (
                getattr(project.network, self.table_name).data if self.table_name != "zones" else project.zoning.data
            )
            fields = fields_from_dataframe(dataframe)
            sink, destination = self.parameterAsSink(
                parameters,
                self.OUTPUT,
                context,
                fields,
                self.sink_geometry_type,
                project_crs(),
            )
            if sink is None:
                raise QgsProcessingException(self.tr("Could not create the output layer"))
            count = add_dataframe_to_sink(dataframe, sink, fields, feedback)
        feedback.pushInfo(self.tr(f"Extracted {count} {self.table_name}"))
        return {self.OUTPUT: destination}

    def shortHelpString(self):
        return self.tr(f"Extracts {self.table_name} from an AequilibraE project.")


def project_crs():
    from qgis.core import QgsCoordinateReferenceSystem

    return QgsCoordinateReferenceSystem("EPSG:4326")


class ExtractLinks(ExtractProjectLayer):
    algorithm_name = "extract_links"
    display_name = "Extract links"
    table_name = "links"
    geometry_type = Qgis.ProcessingSourceType.VectorLine


class ExtractNodes(ExtractProjectLayer):
    algorithm_name = "extract_nodes"
    display_name = "Extract nodes"
    table_name = "nodes"
    geometry_type = Qgis.ProcessingSourceType.VectorPoint
    sink_geometry_type = Qgis.WkbType.Point


class ExtractZones(ExtractProjectLayer):
    algorithm_name = "extract_zones"
    display_name = "Extract zones"
    table_name = "zones"
    geometry_type = Qgis.ProcessingSourceType.VectorPolygon
    sink_geometry_type = Qgis.WkbType.MultiPolygon

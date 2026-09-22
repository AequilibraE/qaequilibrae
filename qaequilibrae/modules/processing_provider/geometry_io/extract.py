"""Algorithms that export project geometry to Processing sinks."""

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsWkbTypes,
)

from ..project_algorithm import ProjectAlgorithm
from .common import add_dataframe_to_sink, fields_from_dataframe
from .project import open_project


class ExtractProjectLayer(ProjectAlgorithm):
    """Base class for exporting one project table as a vector layer."""

    OUTPUT = "OUTPUT"
    group_name = "Geometry IO"
    group_id = "geometry_io"
    table_name = ""
    geometry_type = Qgis.ProcessingSourceType.VectorLine
    sink_geometry_type = QgsWkbTypes.LineString
    display_name = ""
    algorithm_name = ""

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr(self.display_name), type=self.geometry_type))

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.project_folder(parameters, context)
        with open_project(project_folder) as project:
            dataframe = getattr(project.network, self.table_name).data if self.table_name != "zones" else project.zoning.data
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

    def name(self):
        return self.algorithm_name

    def displayName(self):
        return self.tr(self.display_name)

    def shortHelpString(self):
        return self.tr(f"Extracts {self.table_name} from an AequilibraE project.")

    def createInstance(self):
        return type(self)()

def project_crs():
    from qgis.core import QgsCoordinateReferenceSystem

    return QgsCoordinateReferenceSystem("EPSG:4326")


class ExtractLinks(ExtractProjectLayer):
    table_name = "links"
    geometry_type = Qgis.ProcessingSourceType.VectorLine
    display_name = "Extract links"
    algorithm_name = "extract_links"


class ExtractNodes(ExtractProjectLayer):
    table_name = "nodes"
    geometry_type = Qgis.ProcessingSourceType.VectorPoint
    sink_geometry_type = QgsWkbTypes.Point
    display_name = "Extract nodes"
    algorithm_name = "extract_nodes"


class ExtractZones(ExtractProjectLayer):
    table_name = "zones"
    geometry_type = Qgis.ProcessingSourceType.VectorPolygon
    sink_geometry_type = QgsWkbTypes.MultiPolygon
    display_name = "Extract zones"
    algorithm_name = "extract_zones"

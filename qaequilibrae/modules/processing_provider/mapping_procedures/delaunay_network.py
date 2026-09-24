"""Delaunay-network Processing algorithm built on AequilibraE's DelaunayAnalysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.common_tools.sql_identifiers import quote_identifier

from ..geometry_io.common import add_dataframe_to_sink, fields_from_dataframe
from ..project import open_project
from ..project_algorithm import ProjectAlgorithm

if TYPE_CHECKING:
    import pandas as pd


class DelaunayNetwork(ProjectAlgorithm):
    """Build a Delaunay triangulation of a project's centroids and assign a matrix."""

    SOURCE = "SOURCE"
    OVERWRITE = "OVERWRITE"
    MATRIX_NAME = "MATRIX_NAME"
    MATRIX_CORES = "MATRIX_CORES"
    RESULT_NAME = "RESULT_NAME"
    OUTPUT = "OUTPUT"
    RESULT = "RESULT"

    group_name = "Mapping"
    group_id = "mapping"

    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        self.add_project_folder_parameter()
        self.addParameter(
            QgsProcessingParameterEnum(
                self.SOURCE,
                self.tr("Centroid source"),
                options=[self.tr("Zones"), self.tr("Network")],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OVERWRITE,
                self.tr("Overwrite an existing Delaunay network"),
                defaultValue=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.MATRIX_NAME,
                self.tr("Matrix name to assign (optional)"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.MATRIX_CORES,
                self.tr("Matrix cores to assign (comma-separated, all by default)"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.RESULT_NAME,
                self.tr("Result name"),
                defaultValue="delaunay",
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Delaunay network"),
                type=Qgis.ProcessingSourceType.VectorLine,
            )
        )
        self.addOutput(QgsProcessingOutputString(self.RESULT, self.tr("Saved result name")))

    def processAlgorithm(
        self, parameters: dict[str, Any], context: QgsProcessingContext, feedback: QgsProcessingFeedback | None
    ) -> dict[str, Any]:
        if feedback is None:
            feedback = QgsProcessingFeedback()
        project_folder = self.project_folder(parameters, context)
        source = ("zones", "network")[self.parameterAsEnum(parameters, self.SOURCE, context)]
        overwrite = self.parameterAsBool(parameters, self.OVERWRITE, context)
        matrix_name = self.parameterAsString(parameters, self.MATRIX_NAME, context) or None
        cores = self.parameterAsString(parameters, self.MATRIX_CORES, context)
        result_name = self.parameterAsString(parameters, self.RESULT_NAME, context) or "delaunay"

        try:
            with open_project(project_folder) as project:
                from aequilibrae.utils.create_delaunay_network import DelaunayAnalysis

                feedback.pushInfo(self.tr("Creating the Delaunay network"))
                analysis = DelaunayAnalysis(project)
                analysis.create_network(source=source, overwrite=overwrite)

                assigned = False
                if matrix_name:
                    assigned = self._assign_matrix(project, analysis, matrix_name, cores, result_name, feedback)
                dataframe = self._read_network(project, result_name if assigned else None)
        except QgsProcessingException:
            raise
        except Exception as error:
            raise QgsProcessingException(self.tr(f"Could not create Delaunay network: {error}")) from error

        fields = fields_from_dataframe(dataframe)
        sink, destination = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            Qgis.WkbType.LineString,
            QgsCoordinateReferenceSystem("EPSG:4326"),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))
        count = add_dataframe_to_sink(dataframe, sink, fields, feedback)

        feedback.pushInfo(self.tr(f"Wrote {count} Delaunay links"))
        outputs = {self.OUTPUT: destination, self.RESULT: result_name if assigned else ""}
        return outputs

    def _assign_matrix(
        self,
        project: Any,
        analysis: Any,
        matrix_name: str,
        cores: str,
        result_name: str,
        feedback: QgsProcessingFeedback,
    ) -> bool:
        matrix = project.matrices.get_matrix(matrix_name)
        try:
            selected_cores = (
                [core.strip() for core in cores.split(",") if core.strip()] if cores else list(matrix.names)
            )
            if not selected_cores:
                raise ValueError("At least one matrix core is required")
            matrix.computational_view(selected_cores)
            feedback.pushInfo(self.tr("Assigning the matrix to the Delaunay network"))
            analysis.assign_matrix(matrix, result_name)
        finally:
            matrix.close()
        return True

    @staticmethod
    def _read_network(project: Any, result_name: str | None) -> pd.DataFrame:
        import pandas as pd
        import shapely.wkb

        with project.db_connection as conn:
            links = pd.read_sql(
                "SELECT link_id, direction, a_node, b_node, distance, "
                "st_asBinary(geometry) AS geometry FROM delaunay_network",
                conn,
            )
        links["geometry"] = links["geometry"].apply(shapely.wkb.loads)
        if result_name:
            with project.results_connection as conn:
                results = pd.read_sql(f"SELECT * FROM {quote_identifier(result_name)}", conn).set_index("link_id")
            links = links.join(results, on="link_id")
        return links

    def name(self) -> str:
        return "delaunay_network"

    def displayName(self) -> str:
        return self.tr("Delaunay network")

    def shortHelpString(self) -> str:
        return self.tr(
            "Builds a Delaunay triangulation from the project's zone centroids or network "
            "centroid nodes, using AequilibraE's DelaunayAnalysis. The algorithm creates or "
            "replaces the project's delaunay_network table. If a project matrix is selected, "
            "the chosen cores are assigned and the result is saved in the project results "
            "database. Zone IDs or centroid node IDs must match the matrix index. The output "
            "line layer includes link attributes and, when assigned, AB/BA/total flow fields."
        )

    def createInstance(self) -> QgsProcessingAlgorithm:
        return DelaunayNetwork()

    def tags(self) -> list[str]:
        return ["delaunay", "desire", "lines", "mapping", "triangulation"]

    def tr(self, message: str) -> str:
        return trlt("DelaunayNetwork", message)

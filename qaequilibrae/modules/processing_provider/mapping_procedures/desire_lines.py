"""Desire-line operation and its QGIS Processing adapter.

The operation turns a matrix and a set of centroid coordinates into one line per
unordered origin-destination pair, with an AB and a BA flow for every matrix core.
The :class:`DesireLines` adapter reads the matrix and centroids from QGIS inputs
and writes the result to a feature sink; the desktop dialog reuses the operation.
"""

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import pandas as pd
from shapely.geometry import LineString

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt

from ..geometry_io.common import add_dataframe_to_sink, fields_from_dataframe


class MatrixLike(Protocol):
    """Matrix interface required by :func:`compute_desire_lines`."""

    view_names: Sequence[str] | None
    index: Any

    def get_matrix(self, core: str) -> np.ndarray:
        """Return the selected matrix core as a two-dimensional array."""
        ...


def compute_desire_lines(
    centroids: Mapping[int, tuple[float, float]], matrix: MatrixLike
) -> tuple[pd.DataFrame, list[str], float]:
    """Return desire lines as ``(dataframe, report, unassigned_flow)``.

    ``centroids`` maps a zone ID to its ``(x, y)`` point. ``matrix`` must already
    have its computational view set to the cores that should be used. The
    dataframe holds one row per unordered pair that carries any flow, with
    ``{core}_AB`` and ``{core}_BA`` columns and a Shapely geometry. IDs missing
    from ``centroids`` are excluded and their associated flow is included in the
    report total. Intrazonal demand is omitted. Each pair is oriented from the
    higher zone ID to the lower: AB is that direction and BA is the reverse.
    """
    cores = list(matrix.view_names or ())
    if not cores:
        raise ValueError("The matrix computational view contains no cores")
    index = np.asarray(matrix.index[:], dtype=np.int64)
    zones = index.shape[0]
    zone_position = {int(zone): position for position, zone in enumerate(index)}

    core_matrices = {core: matrix.get_matrix(core) for core in cores}
    total = np.zeros((zones, zones), np.float64)
    for core_matrix in core_matrices.values():
        total += core_matrix

    report = []
    unassigned = 0.0
    for zone in index:
        if int(zone) not in centroids:
            position = zone_position[int(zone)]
            flow = (
                np.nansum(total[position, :]) + np.nansum(total[:, position]) - 2 * np.nansum(total[position, position])
            )
            unassigned += flow
            report.append(f"Zone {zone} does not have a corresponding centroid/zone. Total flow {flow}")
            total[position, :] = 0
            total[:, position] = 0

    records = []
    pairs = []
    for origin_position, origin in enumerate(index):
        for destination_position, destination in enumerate(index):
            if origin <= destination:
                continue
            if total[origin_position, destination_position] != 0 or total[destination_position, origin_position] != 0:
                pairs.append((int(origin), int(destination), origin_position, destination_position))
    pairs.sort(key=lambda pair: (pair[0], pair[1]))

    for sequence, (a_node, b_node, a_position, b_position) in enumerate(pairs, start=1):
        line = LineString([centroids[a_node], centroids[b_node]])
        row = {
            "link_id": sequence,
            "a_node": a_node,
            "b_node": b_node,
            "direction": 0,
            "distance": float(line.length),
        }
        row.update({f"{core}_AB": float(core_matrices[core][a_position, b_position]) for core in cores})
        row.update({f"{core}_BA": float(core_matrices[core][b_position, a_position]) for core in cores})
        row["geometry"] = line
        records.append(row)

    columns = ["link_id", "a_node", "b_node", "direction", "distance"]
    columns.extend(f"{core}_AB" for core in cores)
    columns.extend(f"{core}_BA" for core in cores)
    columns.append("geometry")
    dataframe = pd.DataFrame(records, columns=columns)
    for field in ("link_id", "a_node", "b_node", "direction"):
        dataframe[field] = dataframe[field].astype(np.int64)
    for field in ("distance", *(f"{core}_{direction}" for core in cores for direction in ("AB", "BA"))):
        dataframe[field] = dataframe[field].astype(np.float64)
    return dataframe, report, unassigned


class DesireLines(QgsProcessingAlgorithm):
    """Create desire lines for the flows in a matrix."""

    ZONES = "ZONES"
    ZONE_ID_FIELD = "ZONE_ID_FIELD"
    MATRIX_PATH = "MATRIX_PATH"
    MATRIX_CORES = "MATRIX_CORES"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ZONES,
                self.tr("Zone or centroid layer"),
                types=[Qgis.ProcessingSourceType.VectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.ZONE_ID_FIELD,
                self.tr("Zone ID field"),
                parentLayerParameterName=self.ZONES,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.MATRIX_PATH,
                self.tr("Matrix file (*.omx)"),
                behavior=Qgis.ProcessingFileParameterBehavior.File,
                fileFilter="OpenMatrix (*.omx)",
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.MATRIX_CORES,
                self.tr("Matrix cores (comma-separated, all by default)"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Desire lines"),
                type=Qgis.ProcessingSourceType.VectorLine,
            )
        )

    def processAlgorithm(
        self, parameters: dict[str, Any], context: QgsProcessingContext, feedback: QgsProcessingFeedback | None
    ) -> dict[str, Any]:
        if feedback is None:
            feedback = QgsProcessingFeedback()
        source = self.parameterAsSource(parameters, self.ZONES, context)
        if source is None:
            raise QgsProcessingException(self.tr("The zone or centroid layer could not be loaded"))
        zone_id_field = self.parameterAsString(parameters, self.ZONE_ID_FIELD, context)
        zone_id_index = source.fields().lookupField(zone_id_field)
        if zone_id_index < 0:
            raise QgsProcessingException(self.tr(f"The zone ID field '{zone_id_field}' does not exist"))
        matrix_path = self.parameterAsFile(parameters, self.MATRIX_PATH, context)
        cores = self.parameterAsString(parameters, self.MATRIX_CORES, context)

        centroids = self._centroids(source, zone_id_index, feedback)
        if feedback.isCanceled():
            return {}
        if not centroids:
            raise QgsProcessingException(self.tr("The zone layer contains no usable centroids"))

        from aequilibrae.matrix import AequilibraeMatrix

        matrix = AequilibraeMatrix()
        try:
            matrix.load(Path(matrix_path))
            selected_cores = (
                [core.strip() for core in cores.split(",") if core.strip()] if cores else list(matrix.names)
            )
            if not selected_cores:
                raise QgsProcessingException(self.tr("The matrix contains no cores"))
            matrix.computational_view(selected_cores)
            dataframe, report, unassigned = compute_desire_lines(centroids, matrix)
        except QgsProcessingException:
            raise
        except Exception as error:
            raise QgsProcessingException(self.tr(f"Could not create desire lines: {error}")) from error
        finally:
            matrix.close()

        for message in report:
            feedback.pushInfo(message)
        if unassigned > 0:
            feedback.pushInfo(self.tr(f"Total non assigned flows (not counting intrazonals): {unassigned}"))
        if dataframe.empty:
            feedback.pushWarning(self.tr("There is nothing to show"))

        fields = fields_from_dataframe(dataframe)
        sink, destination = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            Qgis.WkbType.LineString,
            source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))
        count = add_dataframe_to_sink(dataframe, sink, fields, feedback)
        feedback.pushInfo(self.tr(f"Created {count} desire lines"))
        return {self.OUTPUT: destination}

    @staticmethod
    def _centroids(
        source: QgsFeatureSource, zone_id_index: int, feedback: QgsProcessingFeedback
    ) -> dict[int, tuple[float, float]]:
        centroids = {}
        for feature in cast(Iterable[QgsFeature], source.getFeatures()):
            if feedback.isCanceled():
                break
            geometry = feature.geometry()
            if geometry is None or geometry.isEmpty():
                continue
            point = geometry.centroid().asPoint()
            centroids[int(feature.attributes()[zone_id_index])] = (point.x(), point.y())
        return centroids

    def name(self) -> str:
        return "desire_lines"

    def displayName(self) -> str:
        return self.tr("Desire lines")

    def group(self) -> str:
        return self.tr("Mapping")

    def groupId(self) -> str:
        return "mapping"

    def shortHelpString(self) -> str:
        return self.tr(
            "Creates one line for each non-intrazonal zone pair with flow. The zone ID field "
            "must contain integer IDs that match the OpenMatrix (*.omx) index. Select matrix "
            "cores as a comma-separated list, or leave the field empty to use all cores. IDs "
            "without geometry are excluded and their flows are reported. AB records flow from "
            "the higher ID to the lower ID; BA records the reverse. Line geometry and distance "
            "use the input layer CRS."
        )

    def createInstance(self) -> QgsProcessingAlgorithm:
        return DesireLines()

    def tags(self) -> list[str]:
        return ["desire", "lines", "mapping", "matrix", "flow"]

    def tr(self, message: str) -> str:
        return trlt("DesireLines", message)

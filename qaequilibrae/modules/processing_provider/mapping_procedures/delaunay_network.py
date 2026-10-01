"""Standalone Delaunay-network Processing algorithm."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from shapely.geometry import LineString

from qgis.core import (
    Qgis,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)

from qaequilibrae.modules.common_tools.vector_layer_helpers import centroid_coordinates
from qaequilibrae.modules.processing_provider.project_algorithm import ProcessingAlgorithm

from ..geometry_io.common import add_dataframe_to_sink, fields_from_dataframe
from ..matrix import open_matrix


def compute_delaunay_network(
    nodes: dict[int, tuple[float, float]], matrix: Any | None = None, *, block_centroid_flows: bool = True
) -> pd.DataFrame:
    """Create Delaunay edges and optionally assign matrix demand to them."""
    if len(nodes) < 3:
        raise ValueError("At least three nodes are required to create a Delaunay network")

    node_ids = np.asarray(list(nodes), dtype=np.int64)
    coordinates = np.asarray([nodes[int(node)] for node in node_ids], dtype=np.float64)
    triangulation = Delaunay(coordinates)
    edges = {
        tuple(sorted((int(node_ids[left]), int(node_ids[right]))))
        for simplex in triangulation.simplices
        for left, right in ((simplex[0], simplex[1]), (simplex[1], simplex[2]), (simplex[2], simplex[0]))
    }

    records = []
    for link_id, (a_node, b_node) in enumerate(sorted(edges), start=1):
        line = LineString([nodes[a_node], nodes[b_node]])
        row: dict[str, Any] = {
            "link_id": link_id,
            "direction": 0,
            "a_node": a_node,
            "b_node": b_node,
            "distance": float(line.length),
        }
        row["geometry"] = line
        records.append(row)

    columns = ["link_id", "direction", "a_node", "b_node", "distance", "geometry"]
    dataframe = pd.DataFrame(records, columns=columns)
    if matrix is None:
        return dataframe

    from aequilibrae.paths import Graph, TrafficAssignment, TrafficClass

    graph = Graph()
    graph.mode = "delaunay"
    graph.network = dataframe[["link_id", "direction", "a_node", "b_node", "distance"]].copy()
    graph.network["capacity"] = 1.0
    graph.prepare_graph(np.asarray(sorted(nodes), dtype=np.int64))
    graph.set_blocked_centroid_flows(block_centroid_flows)

    traffic_class = TrafficClass("delaunay", graph, matrix)
    assignment = TrafficAssignment()
    assignment.set_classes([traffic_class])
    assignment.set_time_field("distance")
    assignment.set_capacity_field("capacity")
    assignment.set_vdf("BPR")
    assignment.set_vdf_parameters({"alpha": 0, "beta": 1.0})
    assignment.set_algorithm("all-or-nothing")
    assignment.execute()

    flow_columns = [field for core in matrix.view_names for field in (f"{core}_ab", f"{core}_ba", f"{core}_tot")]
    flows = assignment.results()[flow_columns]
    dataframe = dataframe.join(flows, on="link_id")
    return dataframe


class DelaunayNetwork(ProcessingAlgorithm):
    """Build Delaunay edges from supplied nodes and optionally attach matrix flows."""

    algorithm_name = "delaunay_network"
    display_name = "Delaunay network"
    group_name = "Mapping"
    group_id = "mapping"

    NODES = "NODES"
    NODE_ID_FIELD = "NODE_ID_FIELD"
    MATRIX_PATH = "MATRIX_PATH"
    MATRIX_CORES = "MATRIX_CORES"
    OUTPUT = "OUTPUT"
    BLOCK_CENTROID_FLOWS = "BLOCK_CENTROID_FLOWS"
    matrix: Any | None = None

    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.NODES,
                self.tr("Node or centroid layer"),
                types=[Qgis.ProcessingSourceType.VectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.NODE_ID_FIELD, self.tr("Node ID field"), parentLayerParameterName=self.NODES
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.MATRIX_PATH,
                self.tr("Optional matrix file (*.omx)"),
                behavior=Qgis.ProcessingFileParameterBehavior.File,
                fileFilter="OpenMatrix (*.omx)",
                optional=True,
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
            QgsProcessingParameterBoolean(self.BLOCK_CENTROID_FLOWS, self.tr("Block flows through centroids"), True)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT, self.tr("Delaunay network"), type=Qgis.ProcessingSourceType.VectorLine
            )
        )

    def processAlgorithm(
        self, parameters: dict[str, Any], context: QgsProcessingContext, feedback: QgsProcessingFeedback | None
    ) -> dict[str, Any]:
        feedback = feedback or QgsProcessingFeedback()
        source = self.parameterAsSource(parameters, self.NODES, context)
        if source is None:
            raise QgsProcessingException(self.tr("The node or centroid layer could not be loaded"))
        node_id_field = self.parameterAsString(parameters, self.NODE_ID_FIELD, context)
        node_id_index = source.fields().lookupField(node_id_field)
        if node_id_index < 0:
            raise QgsProcessingException(self.tr(f"The node ID field '{node_id_field}' does not exist"))

        nodes = centroid_coordinates(source, node_id_index, feedback)
        if len(nodes) < 3:
            raise QgsProcessingException(self.tr("At least three usable nodes are required"))

        matrix_path = self.parameterAsFile(parameters, self.MATRIX_PATH, context)
        cores = self.parameterAsString(parameters, self.MATRIX_CORES, context)
        try:
            matrix_context = (
                open_matrix(matrix_path, cores, self.matrix)
                if matrix_path or self.matrix is not None
                else nullcontext()
            )
            with matrix_context as matrix:
                dataframe = compute_delaunay_network(
                    nodes,
                    matrix,
                    block_centroid_flows=self.parameterAsBool(parameters, self.BLOCK_CENTROID_FLOWS, context),
                )
        except Exception as error:
            raise QgsProcessingException(self.tr(f"Could not create Delaunay network: {error}")) from error

        fields = fields_from_dataframe(dataframe)
        sink, destination = self.parameterAsSink(
            parameters, self.OUTPUT, context, fields, Qgis.WkbType.LineString, source.sourceCrs()
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))
        count = add_dataframe_to_sink(dataframe, sink, fields, feedback)
        feedback.pushInfo(self.tr(f"Wrote {count} Delaunay links"))
        return {self.OUTPUT: destination}

    def shortHelpString(self) -> str:
        return self.tr(
            "Builds Delaunay edges from the centroids of the supplied node features. The node ID field "
            "must contain integer IDs. An optional OpenMatrix (*.omx) file assigns matrix demand to "
            "the network with an all-or-nothing assignment, adding AB, BA, and total flow fields. Matrix "
            "IDs must match node IDs. Geometry and distance use "
            "the input layer CRS."
        )

    def tags(self) -> list[str]:
        return ["delaunay", "lines", "mapping", "triangulation"]

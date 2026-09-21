"""Shortest-path operation and its QGIS Processing adapter.

The routing operation receives a tabular AequilibraE network and returns plain
Python data. The :class:`ShortestPath` adapter translates QGIS inputs and outputs
around it, keeping the routing logic independent from the desktop dialog.
"""

from dataclasses import dataclass
from typing import Iterable

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputNumber,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QMetaType

from qaequilibrae.i18n.translate import trlt

from .network_dataframe import network_dataframe_from_source


class ShortestPathError(ValueError):
    """An input or routing error that callers can present in their own way."""


@dataclass(frozen=True)
class PathSegment:
    """One directed link in a path, expressed using model node IDs."""

    link_id: int
    a_node: int
    b_node: int
    direction: int
    cost: float


@dataclass(frozen=True)
class ShortestPathResult:
    """The ordered path returned by :func:`compute_shortest_path`."""

    segments: tuple[PathSegment, ...]

    @property
    def link_ids(self) -> tuple[int, ...]:
        """Return link IDs in traversal order."""
        return tuple(segment.link_id for segment in self.segments)

    @property
    def total_cost(self) -> float:
        """Return the sum of the directed-link costs."""
        return sum(segment.cost for segment in self.segments)


def parse_excluded_link_ids(value: str) -> tuple[int, ...]:
    """Parse the compact link-ID form used by Processing and the dialog."""
    if not value.strip():
        return ()

    try:
        return tuple(int(link_id.strip()) for link_id in value.split(",") if link_id.strip())
    except ValueError as error:
        raise ShortestPathError("Excluded link IDs must be integers separated by commas") from error


def compute_shortest_path(
    network,
    mode: str,
    cost_field: str,
    from_node: int,
    to_node: int,
    *,
    centroid_node_ids: Iterable[int] | None = None,
    excluded_link_ids: Iterable[int] = (),
) -> ShortestPathResult:
    """Compute a path from a tabular AequilibraE network.

    ``network`` must use AequilibraE's standard link columns. Callers read their
    source and decide how to report :class:`ShortestPathError`.
    """
    try:
        import numpy as np
        import pandas as pd
        from aequilibrae.paths import Graph
        from aequilibrae.paths.results import PathResults
    except ImportError as error:
        raise ShortestPathError(f"Could not load shortest-path dependencies: {error}") from error

    mode = mode.strip()
    cost_field = cost_field.lower()
    if not mode:
        raise ShortestPathError("A mode is required")

    data = _network_for_mode(network, mode, cost_field, pd, np)
    centroids = _centroid_array(centroid_node_ids, data, np)

    try:
        graph = Graph()
        graph.network = data
        graph.prepare_graph(centroids)

        excluded_link_ids = list(excluded_link_ids)
        if excluded_link_ids:
            graph.exclude_links(excluded_link_ids)

        graph.set_graph(cost_field)
        graph.set_skimming([cost_field])
        graph.set_blocked_centroid_flows(centroid_node_ids is not None)

        results = PathResults()
        results.prepare(graph)
        results.compute_path(from_node, to_node)
    except Exception as error:
        raise ShortestPathError(f"Could not compute the shortest path: {error}") from error

    if results.path is None:
        raise ShortestPathError(f"No path between {from_node} and {to_node}")

    return ShortestPathResult(_path_segments(results, graph, cost_field))


def _network_for_mode(network, mode, cost_field, pd, np):
    """Validate, filter, and copy input into AequilibraE's required layout."""
    if not isinstance(network, pd.DataFrame):
        raise ShortestPathError("The network must be a pandas DataFrame")

    network = network.copy(deep=True)
    network.columns = [str(column).lower() for column in network.columns]
    required_columns = {"link_id", "a_node", "b_node", "direction", "modes", cost_field}
    missing_columns = required_columns.difference(network.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ShortestPathError(f"The network is missing required field(s): {missing}")

    mode_mask = network["modes"].astype("string").str.contains(mode, na=False, regex=False)
    network = network.loc[mode_mask].copy()
    if network.empty:
        raise ShortestPathError(f"No link supports mode '{mode}'")

    # Direction-specific costs are optional in AequilibraE. Preserve them when
    # supplied, while still accepting a direction-independent cost field.
    directional_costs = [field for field in (f"{cost_field}_ab", f"{cost_field}_ba") if field in network.columns]
    columns = ["link_id", "a_node", "b_node", "direction", cost_field, *directional_costs]
    return _writable_dataframe(network[columns], pd, np)


def _writable_dataframe(dataframe, pd, np):
    """Copy columns into writable NumPy arrays, as required by AequilibraE."""
    fixed_dtypes = {
        "link_id": np.int64,
        "a_node": np.int64,
        "b_node": np.int64,
        "direction": np.int8,
    }
    data = {}
    for column in dataframe.columns:
        series = dataframe[column]
        dtype = fixed_dtypes.get(column, np.float64 if pd.api.types.is_numeric_dtype(series) else object)
        data[column] = np.require(np.asarray(series.tolist(), dtype=dtype), requirements=["C", "W", "O"])
    return pd.DataFrame(data, copy=False)


def _centroid_array(centroid_node_ids, network, np):
    """Return graph centroids while keeping centroid-flow policy caller controlled."""
    if centroid_node_ids is None:
        return np.asarray([network["a_node"].iloc[0]], dtype=np.int64)

    try:
        centroids = np.asarray(tuple(centroid_node_ids), dtype=np.int64)
    except (TypeError, ValueError) as error:
        raise ShortestPathError(f"Could not read centroid node IDs: {error}") from error
    if not centroids.size:
        raise ShortestPathError("At least one centroid node is required when centroid flows are blocked")
    return centroids


def _path_segments(results, graph, cost_field) -> tuple[PathSegment, ...]:
    """Translate AequilibraE's internal node positions back to model IDs."""
    data = graph.graph.assign(_path_key=graph.graph.link_id * graph.graph.direction)
    records = {int(record["_path_key"]): record for _, record in data.iterrows()}
    segments = []
    for link_id, direction in zip(results.path, results.path_link_directions, strict=True):
        record = records.get(int(link_id) * int(direction))
        if record is None:
            raise ShortestPathError(f"Could not find directed link {link_id} in the routing graph")
        segments.append(
            PathSegment(
                link_id=int(record["link_id"]),
                a_node=int(graph.all_nodes[int(record["a_node"])]),
                b_node=int(graph.all_nodes[int(record["b_node"])]),
                direction=int(record["direction"]),
                cost=float(record[cost_field]),
            )
        )
    return tuple(segments)


class ShortestPath(QgsProcessingAlgorithm):
    """Compute a shortest path from a link layer and write its geometry to a sink."""

    LINKS = "LINKS"
    NODES = "NODES"
    MODE = "MODE"
    COST_FIELD = "COST_FIELD"
    FROM_NODE = "FROM_NODE"
    TO_NODE = "TO_NODE"
    BLOCK_CENTROID_FLOWS = "BLOCK_CENTROID_FLOWS"
    EXCLUDED_LINKS = "EXCLUDED_LINKS"
    OUTPUT = "OUTPUT"
    PATH_LINK_IDS = "PATH_LINK_IDS"
    TOTAL_COST = "TOTAL_COST"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.LINKS,
                self.tr("Links"),
                types=[Qgis.ProcessingSourceType.VectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.NODES,
                self.tr("Nodes (required to block flows through centroids)"),
                types=[Qgis.ProcessingSourceType.VectorPoint],
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterString(self.MODE, self.tr("Mode")))
        self.addParameter(
            QgsProcessingParameterField(
                self.COST_FIELD,
                self.tr("Cost field"),
                type=Qgis.ProcessingFieldParameterDataType.Numeric,
                parentLayerParameterName=self.LINKS,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.FROM_NODE,
                self.tr("From node"),
                type=Qgis.ProcessingNumberParameterType.Integer,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TO_NODE,
                self.tr("To node"),
                type=Qgis.ProcessingNumberParameterType.Integer,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.BLOCK_CENTROID_FLOWS,
                self.tr("Block flows through centroids"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.EXCLUDED_LINKS,
                self.tr("Excluded link IDs (comma-separated)"),
                defaultValue="",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Shortest path"),
                type=Qgis.ProcessingSourceType.VectorLine,
            )
        )
        self.addOutput(QgsProcessingOutputString(self.PATH_LINK_IDS, self.tr("Path link IDs")))
        self.addOutput(QgsProcessingOutputNumber(self.TOTAL_COST, self.tr("Total cost")))

    def processAlgorithm(self, parameters, context, feedback):
        # The algorithm owns QGIS-specific work: resolve sources, report progress, and
        # turn the operation's simple result into a QGIS feature sink.
        links = self.parameterAsSource(parameters, self.LINKS, context)
        if links is None:
            raise QgsProcessingException(self.tr("The links layer could not be loaded"))

        feedback.pushInfo(self.tr("Reading links"))
        network = network_dataframe_from_source(links)
        if feedback.isCanceled():
            return {}

        block_centroid_flows = self.parameterAsBool(parameters, self.BLOCK_CENTROID_FLOWS, context)
        try:
            result = compute_shortest_path(
                network,
                self.parameterAsString(parameters, self.MODE, context),
                self.parameterAsString(parameters, self.COST_FIELD, context),
                self.parameterAsInt(parameters, self.FROM_NODE, context),
                self.parameterAsInt(parameters, self.TO_NODE, context),
                centroid_node_ids=self._centroid_node_ids(parameters, context) if block_centroid_flows else None,
                excluded_link_ids=parse_excluded_link_ids(
                    self.parameterAsString(parameters, self.EXCLUDED_LINKS, context)
                ),
            )
        except ShortestPathError as error:
            raise QgsProcessingException(self.tr(str(error))) from error

        if feedback.isCanceled():
            return {}

        fields = self._output_fields()
        sink, destination = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            Qgis.WkbType.LineString,
            links.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        source_features = self._source_features_by_link_id(links)
        for sequence, segment in enumerate(result.segments, start=1):
            if feedback.isCanceled():
                return {}
            source_feature = source_features.get(segment.link_id)
            if source_feature is None:
                raise QgsProcessingException(self.tr(f"Could not find geometry for link {segment.link_id}"))

            feature = QgsFeature(fields)
            feature.setGeometry(source_feature.geometry())
            feature.setAttributes(
                [sequence, segment.link_id, segment.a_node, segment.b_node, segment.direction, segment.cost]
            )
            sink.addFeature(feature)
            feedback.setProgress(sequence * 100 / len(result.segments))

        return {
            self.OUTPUT: destination,
            self.PATH_LINK_IDS: ",".join(str(link_id) for link_id in result.link_ids),
            self.TOTAL_COST: result.total_cost,
        }

    def _centroid_node_ids(self, parameters, context):
        nodes = self.parameterAsSource(parameters, self.NODES, context)
        if nodes is None:
            raise ShortestPathError("A nodes layer is required to block flows through centroids")

        node_id_index = nodes.fields().lookupField("node_id")
        centroid_index = nodes.fields().lookupField("is_centroid")
        if node_id_index < 0 or centroid_index < 0:
            raise ShortestPathError("The nodes layer requires node_id and is_centroid fields")

        centroids = []
        features = nodes.getFeatures()
        feature = QgsFeature()
        while features.nextFeature(feature):
            if feature.attribute(centroid_index) in (True, 1, "1"):
                centroids.append(feature.attribute(node_id_index))
        return tuple(centroids)

    def _source_features_by_link_id(self, links):
        link_id_index = links.fields().lookupField("link_id")
        if link_id_index < 0:
            raise QgsProcessingException(self.tr("The links layer requires a link_id field"))
        features_by_link_id = {}
        features = links.getFeatures()
        feature = QgsFeature()
        while features.nextFeature(feature):
            features_by_link_id[int(feature.attribute(link_id_index))] = QgsFeature(feature)
        return features_by_link_id

    @staticmethod
    def _output_fields():
        fields = QgsFields()
        fields.append(QgsField("sequence", QMetaType.Type.Int))
        fields.append(QgsField("link_id", QMetaType.Type.LongLong))
        fields.append(QgsField("a_node", QMetaType.Type.LongLong))
        fields.append(QgsField("b_node", QMetaType.Type.LongLong))
        fields.append(QgsField("direction", QMetaType.Type.Int))
        fields.append(QgsField("cost", QMetaType.Type.Double))
        return fields

    def name(self):
        return "shortest_path"

    def displayName(self):
        return self.tr("Shortest path")

    def group(self):
        return self.tr("Path computation")

    def groupId(self):
        return "path_computation"

    def shortHelpString(self):
        return self.tr(
            "Computes the lowest-cost path between two network nodes. The output has one feature per directed link."
        )

    def createInstance(self):
        return ShortestPath()

    def tags(self):
        return ["shortest", "path", "routing"]

    def tr(self, message):
        return trlt("ShortestPath", message)

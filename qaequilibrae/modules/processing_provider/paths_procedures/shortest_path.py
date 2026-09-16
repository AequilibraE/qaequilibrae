from qgis.PyQt.QtCore import QMetaType
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingOutputString,
)

from qaequilibrae.i18n.translate import trlt


def _runtime_dependencies():
    """Load libraries used only while computing a path.

    Processing providers are imported when QGIS starts the plugin. Loading the
    compiled AequilibraE routing extension at that point can make QGIS disable
    the entire plugin when only this algorithm's dependencies fail to load.
    """
    try:
        import numpy as np
        from aequilibrae.paths import Graph
        from aequilibrae.paths.results import PathResults
        from qaequilibrae.modules.common_tools import geodataframe_from_layer
        from qaequilibrae.modules.common_tools.writable_dataframe import make_writable_network_dataframe
    except ImportError as exception:
        raise QgsProcessingException(
            trlt("ShortestPath", f"Could not load shortest-path dependencies: {exception}")
        ) from exception

    return Graph, PathResults, geodataframe_from_layer, make_writable_network_dataframe, np


class ShortestPath(QgsProcessingAlgorithm):
    """Computes a shortest path in an AequilibraE network."""

    LINKS = "LINKS"
    NODES = "NODES"
    MODE = "MODE"
    COST_FIELD = "COST_FIELD"
    FROM_NODE = "FROM_NODE"
    TO_NODE = "TO_NODE"
    BLOCK_CENTROID_FLOWS = "BLOCK_CENTROID_FLOWS"
    EXCLUDED_LINKS = "EXCLUDED_LINKS"
    OUTPUT = "OUTPUT"
    PATH_LINKS = "PATH_LINKS"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.LINKS,
                self.tr("Links"),
                types=[QgsProcessing.SourceType.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.NODES,
                self.tr("Nodes (required to block flows through centroids)"),
                types=[QgsProcessing.SourceType.TypeVectorPoint],
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterString(self.MODE, self.tr("Mode")))
        self.addParameter(
            QgsProcessingParameterField(
                self.COST_FIELD,
                self.tr("Cost field"),
                type=QgsProcessingParameterField.DataType.Numeric,
                parentLayerParameterName=self.LINKS,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.FROM_NODE,
                self.tr("From node"),
                type=QgsProcessingParameterNumber.Integer,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TO_NODE,
                self.tr("To node"),
                type=QgsProcessingParameterNumber.Integer,
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
                type=QgsProcessing.SourceType.TypeVectorLine,
            )
        )
        self.addOutput(QgsProcessingOutputString(self.PATH_LINKS, self.tr("Path link IDs")))

    def processAlgorithm(self, parameters, context, feedback):
        Graph, PathResults, geodataframe_from_layer, make_writable_network_dataframe, np = _runtime_dependencies()

        links = self.parameterAsSource(parameters, self.LINKS, context)
        if links is None:
            raise QgsProcessingException(self.tr("The links layer could not be loaded"))

        network = geodataframe_from_layer(links)
        mode = self.parameterAsString(parameters, self.MODE, context).strip()
        cost_field = self.parameterAsString(parameters, self.COST_FIELD, context).lower()

        if "modes" not in network.columns:
            raise QgsProcessingException(self.tr("Your network does not have mode information"))

        mode_mask = network["modes"].astype("string").str.contains(mode, na=False, regex=False)
        network = network.loc[mode_mask].copy(deep=True).infer_objects()
        if network.empty:
            raise QgsProcessingException(self.tr("No link with the selected mode"))

        required_fields = {
            "link_id",
            "a_node",
            "b_node",
            "direction",
            cost_field,
        }
        missing_fields = required_fields.difference(network.columns)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise QgsProcessingException(self.tr(f"The network is missing required field(s): {missing}"))

        cost_fields = {cost_field, f"{cost_field}_ab", f"{cost_field}_ba"}
        network = network[[field for field in network.columns if field in required_fields | cost_fields]]
        network = make_writable_network_dataframe(network)

        block_centroid_flows = self.parameterAsBool(parameters, self.BLOCK_CENTROID_FLOWS, context)
        nodes = self.parameterAsSource(parameters, self.NODES, context) if block_centroid_flows else None
        centroids = self._graph_centroids(network, nodes, np, block_centroid_flows)

        graph = Graph()
        graph.network = network
        graph.prepare_graph(centroids)

        excluded_links = self._excluded_links(parameters, context)
        if excluded_links:
            graph.exclude_links(excluded_links)

        graph.set_graph(cost_field)
        graph.set_skimming([cost_field])
        graph.set_blocked_centroid_flows(block_centroid_flows)

        if feedback.isCanceled():
            return {}

        results = PathResults()
        results.prepare(graph)
        from_node = self.parameterAsInt(parameters, self.FROM_NODE, context)
        to_node = self.parameterAsInt(parameters, self.TO_NODE, context)
        results.compute_path(from_node, to_node)

        if results.path is None:
            raise QgsProcessingException(self.tr(f"No path between {from_node} and {to_node}"))

        fields, path_data = self._path_features(results, graph, links, np)
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

        for feature in path_data:
            if feedback.isCanceled():
                return {}
            sink.addFeature(feature)

        path_links = ",".join(str(int(link_id)) for link_id in results.path)
        return {self.OUTPUT: destination, self.PATH_LINKS: path_links}

    def _graph_centroids(self, network, nodes, np, block_centroid_flows):
        if not block_centroid_flows:
            # AequilibraE requires at least one graph centroid even when it will not block flows.
            return np.asarray([network["a_node"].iloc[0]], dtype=np.int64)

        if nodes is None:
            raise QgsProcessingException(self.tr("A nodes layer is required to block flows through centroids"))

        node_id = nodes.fields().lookupField("node_id")
        is_centroid = nodes.fields().lookupField("is_centroid")
        if node_id < 0 or is_centroid < 0:
            raise QgsProcessingException(self.tr("The nodes layer requires node_id and is_centroid fields"))

        try:
            centroids = np.asarray(
                [feature.attribute(node_id) for feature in nodes.getFeatures() if feature.attribute(is_centroid)],
                dtype=np.int64,
            )
        except (TypeError, ValueError) as exception:
            raise QgsProcessingException(self.tr(f"Could not read centroid node IDs: {exception}")) from exception

        if not centroids.size:
            raise QgsProcessingException(self.tr("The nodes layer does not contain any centroid nodes"))
        return centroids

    def _excluded_links(self, parameters, context):
        raw_links = self.parameterAsString(parameters, self.EXCLUDED_LINKS, context)
        if not raw_links:
            return []

        try:
            return [int(link_id.strip()) for link_id in raw_links.split(",") if link_id.strip()]
        except ValueError as exception:
            raise QgsProcessingException(
                self.tr("Excluded link IDs must be integers separated by commas")
            ) from exception

    def _path_features(self, results, graph, links, np):
        link_field_index = links.fields().lookupField("link_id")
        link_features = {int(feature.attributes()[link_field_index]): feature for feature in links.getFeatures()}

        data = graph.graph.assign(__data_key__=graph.graph.link_id * graph.graph.direction)
        excluded_fields = {
            "link_id",
            "a_node",
            "b_node",
            "direction",
            "__data_key__",
            "id",
            "__supernet_id__",
            "__compressed_id__",
        }
        added_fields = [field for field in data if field not in excluded_fields]

        fields = QgsFields()
        fields.append(QgsField("link_id", QMetaType.Type.LongLong))
        fields.append(QgsField("a_node", QMetaType.Type.LongLong))
        fields.append(QgsField("b_node", QMetaType.Type.LongLong))
        fields.append(QgsField("direction", QMetaType.Type.Int))
        for field in added_fields:
            fields.append(QgsField(field, QMetaType.Type.Double))

        path_keys = np.asarray(results.path) * np.asarray(results.path_link_directions)
        data = data[data["__data_key__"].isin(path_keys)]
        features = []
        for _, record in data.iterrows():
            source_feature = link_features.get(int(record.link_id))
            if source_feature is None:
                continue

            attributes = [
                int(record.link_id),
                int(graph.all_nodes[int(record.a_node)]),
                int(graph.all_nodes[int(record.b_node)]),
                int(record.direction),
            ]
            attributes.extend(float(record[field]) for field in added_fields)

            feature = QgsFeature(fields)
            feature.setGeometry(source_feature.geometry())
            feature.setAttributes(attributes)
            features.append(feature)

        return fields, features

    def name(self):
        return "shortest_path"

    def displayName(self):
        return self.tr("Shortest path")

    def group(self):
        return self.tr("Path computation")

    def groupId(self):
        return "path_computation"

    def shortHelpString(self):
        return self.tr("Computes and optionally exports the shortest path between two network nodes.")

    def createInstance(self):
        return ShortestPath()

    def tags(self):
        return ["shortest", "path", "routing"]

    def tr(self, message):
        return trlt("ShortestPath", message)

import itertools
import struct
from collections import OrderedDict

import numpy as np
import pandas as pd
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import Graph
from aequilibrae.paths import allOrNothing
from aequilibrae.paths.results import AssignmentResults
from aequilibrae.utils.interface.worker_thread import WorkerThread
from qgis.PyQt.QtCore import pyqtSignal, QMetaType
from qgis.core import QgsVectorLayer, QgsField, QgsPointXY, QgsGeometry, QgsFeature
from scipy.spatial import Delaunay

from qaequilibrae.modules.common_tools import get_vector_layer_by_name
from qaequilibrae.modules.processing_provider.mapping_procedures.desire_lines import compute_desire_lines
from qaequilibrae.qgis_logging import get_logger


class DesireLinesProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(
        self, parentThread, layer: str, id_field: int, matrix: AequilibraeMatrix, matrix_hash: dict, dl_type: str
    ) -> None:
        WorkerThread.__init__(self, parentThread)
        self.layer = layer
        self.id_field = id_field
        self.matrix = matrix
        self.dl_type = dl_type
        self.error = None
        self.matrix_hash = matrix_hash
        self.report = []
        self.logger = get_logger(__name__)
        self.nodes_to_indices = {matrix.index[x]: x for x in range(matrix.zones)}
        self.python_version = 8 * struct.calcsize("P")

        self.procedure = "ASSIGNMENT"

    def doWork(self):
        if self.error is None:
            # In case we have only one class

            if self.dl_type == "DesireLines":
                self.do_desire_lines()
            elif self.dl_type == "DelaunayLines":
                self.do_delaunay_lines()

        self.signal.emit(["finished"])

    def get_basic_data(self):
        layer = get_vector_layer_by_name(self.layer)
        idx = layer.dataProvider().fieldNameIndex(self.id_field)
        feature_count = layer.featureCount()
        self.signal.emit(["start", feature_count, "Loading Layer Features"])
        all_centroids = {}
        for P, feat in enumerate(layer.getFeatures()):
            geom = feat.geometry()
            if geom is not None:
                point = list(geom.centroid().asPoint())
                centroid_id = feat.attributes()[idx]
                all_centroids[centroid_id] = point
            self.signal.emit(["update", P, f"Loading Layer Features: {P} / {feature_count}"])
        # Creating resulting layer
        EPSG_code = int(layer.crs().authid().split(":")[1])
        desireline_layer = QgsVectorLayer("LineString?crs=epsg:" + str(EPSG_code), self.dl_type, "memory")
        dlpr = desireline_layer.dataProvider()
        base_dl_fields = [
            QgsField("link_id", QMetaType.Type.Int),
            QgsField("A_Node", QMetaType.Type.Int),
            QgsField("B_Node", QMetaType.Type.Int),
            QgsField("direct", QMetaType.Type.Int),
            QgsField("distance", QMetaType.Type.Double),
        ]
        return all_centroids, base_dl_fields, desireline_layer, dlpr

    def do_desire_lines(self):
        all_centroids, base_dl_fields, desireline_layer, dlpr = self.get_basic_data()

        self.signal.emit(["set_text", self.tr("Manipulating matrix indices")])
        try:
            dataframe, report, unassigned = compute_desire_lines(all_centroids, self.matrix)
        except Exception as error:
            self.error = str(error)
            self.logger.exception("Could not create desire lines")
            return
        self.report.extend(report)

        for core in self.matrix.view_names:
            base_dl_fields.append(QgsField(f"{core}_AB", QMetaType.Type.Double))
        for core in self.matrix.view_names:
            base_dl_fields.append(QgsField(f"{core}_BA", QMetaType.Type.Double))
        dlpr.addAttributes(base_dl_fields)
        desireline_layer.updateFields()

        if dataframe.empty:
            self.report.append("Nothing to show")
            return

        self.signal.emit(["start", len(dataframe), self.tr("Creating Desire Lines")])
        fields = desireline_layer.fields()
        all_features = []
        for i, (_, row) in enumerate(dataframe.iterrows()):
            feature = QgsFeature(fields)
            feature.setGeometry(QgsGeometry.fromWkt(row["geometry"].wkt))
            attributes = [
                int(row["link_id"]),
                int(row["a_node"]),
                int(row["b_node"]),
                int(row["direction"]),
                float(row["distance"]),
            ]
            attributes.extend(float(row[f"{core}_AB"]) for core in self.matrix.view_names)
            attributes.extend(float(row[f"{core}_BA"]) for core in self.matrix.view_names)
            feature.setAttributes(attributes)
            all_features.append(feature)
            self.signal.emit(["update", i, f"Creating lines: {i} / {len(dataframe)}"])

        if all_features:
            _ = dlpr.addFeatures(all_features)
            self.result_layer = desireline_layer
        if unassigned > 0:
            self.report.append(f"Total non assigned flows (not counting intrazonals): {str(unassigned)}")

    def do_delaunay_lines(self):
        all_centroids, base_dl_fields, desireline_layer, dlpr = self.get_basic_data()
        for f in self.matrix.view_names:
            base_dl_fields.extend(
                [
                    QgsField(f + "_ab", QMetaType.Type.Double),
                    QgsField(f + "_ba", QMetaType.Type.Double),
                    QgsField(f + "_tot", QMetaType.Type.Double),
                ]
            )
        dlpr.addAttributes(base_dl_fields)
        desireline_layer.updateFields()

        points = []
        node_id_in_delaunay_results = {}
        i = 0
        self.signal.emit(["start", len(all_centroids), self.tr("Building Delaunay dataset")])
        for k, v in all_centroids.items():
            self.signal.emit(["update", i, f"Building Delaunay dataset: {i}"])
            points.append(v)
            node_id_in_delaunay_results[i] = k
            i += 1
        self.signal.emit(["set_text", self.tr("Computing Delaunay Triangles")])
        tri = Delaunay(np.array(points))
        # We process all the triangles to only get each edge once
        edges = []
        if self.python_version == 32:
            all_edges = tri.vertices
        else:
            all_edges = tri.simplices
        self.signal.emit(["start", len(all_edges), self.tr("Building Delaunay Network: Collecting Edges")])
        for j, triangle in enumerate(all_edges):
            self.signal.emit(["update", j, f"Collecting Edges: {j}"])
            links = list(itertools.combinations(triangle, 2))
            for i in links:
                edges.append([min(i[0], i[1]), max(i[0], i[1])])
        self.signal.emit(["set_text", self.tr("Building Delaunay Network: Getting unique edges")])
        edges = OrderedDict((str(x), x) for x in edges).values()

        # Writing Delaunay layer
        desireline_link_id = 1
        data = []
        dl_ids_on_links = {}
        self.signal.emit(["start", len(edges), self.tr("Building Delaunay Network: Assembling Layer")])
        for j, edge in enumerate(edges):
            self.signal.emit(["update", j, f"Assembling Layer: {j}"])
            a_node = node_id_in_delaunay_results[edge[0]]
            a_point = all_centroids[a_node]
            a_point = QgsPointXY(a_point[0], a_point[1])
            b_node = node_id_in_delaunay_results[edge[1]]
            b_point = all_centroids[b_node]
            b_point = QgsPointXY(b_point[0], b_point[1])
            dist = QgsGeometry().fromPointXY(a_point).distance(QgsGeometry().fromPointXY(b_point))
            line = []
            line.append(desireline_link_id)
            line.append(a_node)
            line.append(b_node)
            line.append(dist)
            line.append(dist)
            line.append(0)
            data.append(line)
            dl_ids_on_links[desireline_link_id] = [a_node, b_node, 0, dist]
            desireline_link_id += 1
        self.signal.emit(["set_text", self.tr("Building graph")])
        network = np.asarray(data)

        net = pd.DataFrame(
            {
                "link_id": network[:, 0],
                "a_node": network[:, 1],
                "b_node": network[:, 2],
                "distance_ab": network[:, 3],
                "distance_ba": network[:, 4],
                "direction": network[:, 5],
            }
        )
        self.graph = Graph()
        itype = self.graph.default_types("int")
        ftype = self.graph.default_types("float")
        all_types = [itype, itype, itype, ftype, ftype, np.int8]
        all_titles = ["link_id", "a_node", "b_node", "distance_ab", "distance_ba", "direction"]

        for tb, nm in zip(all_types, all_titles):
            net[nm] = net[nm].astype(tb)

        self.graph.network = net
        del network
        self.graph.type_loaded = "NETWORK"
        self.graph.status = "OK"
        self.graph.network_ok = True
        self.graph.prepare_graph(self.matrix.index.astype(np.int64))
        self.graph.set_graph(cost_field="distance")
        self.graph.set_blocked_centroid_flows(False)
        self.results = AssignmentResults()
        self.results.prepare(self.graph, self.matrix)
        self.signal.emit(["start", 1, self.tr("Assigning demand")])
        assigner = allOrNothing("aon", self.matrix, self.graph, self.results)
        assigner.execute()
        self.report = assigner.report
        self.signal.emit(["update", 1, self.tr("Collecting results")])
        features = []
        max_edges = len(edges)
        self.signal.emit(["start", max_edges, self.tr("Building resulting layer")])
        link_loads = self.results.get_load_results()
        for i, link_id in enumerate(link_loads.index):
            self.signal.emit(["update", i, f"Building resulting layer: {i}"])
            a_node, b_node, direct, dist = dl_ids_on_links[link_id]

            attr = [int(link_id), a_node, b_node, direct, dist]

            a_point = all_centroids[a_node]
            a_point = QgsPointXY(a_point[0], a_point[1])
            b_point = all_centroids[b_node]
            b_point = QgsPointXY(b_point[0], b_point[1])

            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolylineXY([a_point, b_point]))

            for c in self.matrix.view_names:
                attr.extend(
                    [
                        float(link_loads[c + "_ab"][link_id]),
                        float(link_loads[c + "_ba"][link_id]),
                        float(link_loads[c + "_tot"][link_id]),
                    ]
                )
            feature.setAttributes(attr)
            features.append(feature)
        _ = dlpr.addFeatures(features)
        self.result_layer = desireline_layer

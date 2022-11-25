import itertools
import logging
import struct
from collections import OrderedDict

import numpy as np
import pandas as pd
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import Graph
from aequilibrae.paths.results import AssignmentResults
from numpy.lib import recfunctions as rfn
from qgis._core import QgsVectorLayer, QgsField, QgsPointXY, QgsGeometry, QgsFeature
from scipy.spatial import Delaunay
from PyQt5.QtCore import pyqtSignal
from qgis.PyQt.QtCore import QVariant
from aequilibrae.utils.worker_thread import WorkerThread
from ..common_tools import get_vector_layer_by_name
from aequilibrae.paths import allOrNothing


class DesireLinesProcedure(WorkerThread):
    desire_lines = pyqtSignal(object)

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
        self.logger = logging.getLogger("aequilibrae")
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

        self.desire_lines.emit(("finished_desire_lines_procedure", 0))

    def get_basic_data(self):
        layer = get_vector_layer_by_name(self.layer)
        idx = layer.dataProvider().fieldNameIndex(self.id_field)
        feature_count = layer.featureCount()
        self.desire_lines.emit(("job_size_dl", feature_count))
        all_centroids = {}
        for P, feat in enumerate(layer.getFeatures()):
            geom = feat.geometry()
            if geom is not None:
                point = list(geom.centroid().asPoint())
                centroid_id = feat.attributes()[idx]
                all_centroids[centroid_id] = point
            self.desire_lines.emit(("jobs_done_dl", P))
            self.desire_lines.emit(("text_dl", "Loading Layer Features: " + str(P) + "/" + str(feature_count)))
        # Creating resulting layer
        EPSG_code = int(layer.crs().authid().split(":")[1])
        desireline_layer = QgsVectorLayer("LineString?crs=epsg:" + str(EPSG_code), self.dl_type, "memory")
        dlpr = desireline_layer.dataProvider()
        base_dl_fields = [
            QgsField("link_id", QVariant.Int),
            QgsField("A_Node", QVariant.Int),
            QgsField("B_Node", QVariant.Int),
            QgsField("direct", QVariant.Int),
            QgsField("distance", QVariant.Double),
        ]
        return all_centroids, base_dl_fields, desireline_layer, dlpr

    def do_desire_lines(self):
        all_centroids, base_dl_fields, desireline_layer, dlpr = self.get_basic_data()
        unnasigned = 0
        max_zone = self.matrix.index[:].max().astype(np.int64) + 1
        items = [(i, j[0], j[1]) for i, j in all_centroids.items() if i < max_zone]
        coords = np.array(items)
        coord_index = np.zeros((max_zone, 2))
        coord_index[coords[:, 0].astype(np.int64), 0] = coords[:, 1]
        coord_index[coords[:, 0].astype(np.int64), 1] = coords[:, 2]
        self.desire_lines.emit(("text_dl", "Manipulating matrix indices"))
        zones = self.matrix.index[:].shape[0]
        a = np.array(self.matrix.index[:], np.int64)
        ij, ji = np.meshgrid(a, a, sparse=False, indexing="ij")
        ij = ij.flatten()
        ji = ji.flatten()
        arrays = [ij, ji]
        self.desire_lines.emit(("text_dl", "Collecting all matrices"))
        self.desire_lines.emit(("job_size_dl", len(self.matrix.view_names)))
        total_mat = np.zeros((zones, zones), np.float64)
        for i, mat in enumerate(self.matrix.view_names):
            m = self.matrix.get_matrix(mat)
            total_mat += m
            arrays.append(m.flatten())
            self.desire_lines.emit(("jobs_done_dl", i + 1))
        # Eliminates the cells for which we don't have geography
        self.desire_lines.emit(("text_dl", "Filtering zones with no geography available"))
        zones_with_no_geography = [x for x in self.matrix.index[:] if x not in all_centroids]
        if zones_with_no_geography:
            self.desire_lines.emit(("job_size_dl", len(zones_with_no_geography)))
        for k, z in enumerate(zones_with_no_geography):
            i = self.matrix.matrix_hash[z]
            t = np.nansum(total_mat[i, :]) + np.nansum(total_mat[:, i])
            unnasigned += t
            self.report.append("Zone {} does not have a corresponding centroid/zone. Total flow {}".format(z, t))
            total_mat[i, :] = 0
            total_mat[:, i] = 0
            self.desire_lines.emit(("jobs_done_dl", k + 1))
        self.desire_lines.emit(("text_dl", "Filtering down to OD pairs with flows"))
        field_names = [x for x in self.matrix.view_names]
        nonzero = np.nonzero(total_mat.flatten())
        arrays = np.vstack(arrays).transpose()
        arrays = arrays[nonzero, :]
        arrays = arrays.reshape(arrays.shape[1], arrays.shape[2])
        base_types = [(x, np.float64) for x in ["from", "to"]]
        base_types = base_types + [(f"{x}_AB", np.float64) for x in field_names]
        dtypes_ab = [(x, np.int64) for x in ["from", "to"]] + [(f"{x}_AB", float) for x in field_names]
        dtypes_ba = [(x, np.int64) for x in ["to", "from"]] + [(f"{x}_BA", float) for x in field_names]
        ab_mat = np.array(arrays[arrays[:, 0] > arrays[:, 1], :])
        ba_mat = np.array(arrays[arrays[:, 0] < arrays[:, 1], :])
        flows_ab = ab_mat.view(base_types)
        flows_ab = flows_ab.reshape(flows_ab.shape[:-1])
        flows_ab = flows_ab.astype(dtypes_ab)
        flows_ba = ba_mat.view(base_types)
        flows_ba = flows_ba.reshape(flows_ba.shape[:-1])
        flows_ba = flows_ba.astype(dtypes_ba)
        defaults1 = {x + "_AB": 0.0 for x in field_names}
        defaults = {x + "_BA": 0.0 for x in field_names}
        defaults = {**defaults, **defaults1}
        self.desire_lines.emit(("text_dl", "Concatenating AB & BA flows"))
        flows = rfn.join_by(
            ["from", "to"], flows_ab, flows_ba, jointype="outer", defaults=defaults, usemask=True, asrecarray=True
        )
        flows = flows.filled()
        for f in flows.dtype.names[2:]:
            base_dl_fields.extend([QgsField(f, QVariant.Double)])
        dlpr.addAttributes(base_dl_fields)
        desireline_layer.updateFields()
        self.desire_lines.emit(("text_dl", "Creating Desire Lines"))
        self.desire_lines.emit(("job_size_dl", flows.shape[0]))
        all_features = []
        for i, rec in enumerate(flows):
            a_node = rec[0]
            b_node = rec[1]

            a_point = QgsPointXY(*all_centroids[a_node])
            b_point = QgsPointXY(*all_centroids[b_node])
            dist = QgsGeometry().fromPointXY(a_point).distance(QgsGeometry().fromPointXY(b_point))
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolylineXY([a_point, b_point]))

            attrs = [i + 1, int(a_node), int(b_node), 0, dist]
            attrs.extend([float(x) for x in list(rec)[2:]])
            feature.setAttributes(attrs)
            all_features.append(feature)
            self.desire_lines.emit(("jobs_done_dl", i))
        if unnasigned > 0:
            self.report.append("Total non assigned flows (not counting intrazonals):" + str(unnasigned))
        if flows.shape[0] > 1:
            a = dlpr.addFeatures(all_features)
            self.result_layer = desireline_layer
        else:
            self.report.append("Nothing to show")

    def do_delaunay_lines(self):
        all_centroids, base_dl_fields, desireline_layer, dlpr = self.get_basic_data()
        for f in self.matrix.view_names:
            base_dl_fields.extend(
                [
                    QgsField(f + "_ab", QVariant.Double),
                    QgsField(f + "_ba", QVariant.Double),
                    QgsField(f + "_tot", QVariant.Double),
                ]
            )
        dlpr.addAttributes(base_dl_fields)
        desireline_layer.updateFields()
        self.desire_lines.emit(("text_dl", "Building Delaunay dataset"))
        points = []
        node_id_in_delaunay_results = {}
        i = 0
        self.desire_lines.emit(("job_size_dl", len(all_centroids)))
        for k, v in all_centroids.items():
            self.desire_lines.emit(("jobs_done_dl", i))
            points.append(v)
            node_id_in_delaunay_results[i] = k
            i += 1
        self.desire_lines.emit(("text_dl", "Computing Delaunay Triangles"))
        tri = Delaunay(np.array(points))
        # We process all the triangles to only get each edge once
        self.desire_lines.emit(("text_dl", "Building Delaunay Network: Collecting Edges"))
        edges = []
        if self.python_version == 32:
            all_edges = tri.vertices
        else:
            all_edges = tri.simplices
        self.desire_lines.emit(("job_size_dl", len(all_edges)))
        for j, triangle in enumerate(all_edges):
            self.desire_lines.emit(("jobs_done_dl", j))
            links = list(itertools.combinations(triangle, 2))
            for i in links:
                edges.append([min(i[0], i[1]), max(i[0], i[1])])
        self.desire_lines.emit(("text_dl", "Building Delaunay Network: Getting unique edges"))
        edges = OrderedDict((str(x), x) for x in edges).values()
        # Writing Delaunay layer
        self.desire_lines.emit(("text_dl", "Building Delaunay Network: Assembling Layer"))
        desireline_link_id = 1
        data = []
        dl_ids_on_links = {}
        self.desire_lines.emit(("job_size_dl", len(edges)))
        for j, edge in enumerate(edges):
            self.desire_lines.emit(("jobs_done_dl", j))
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
        self.desire_lines.emit(("text_dl", "Building graph"))
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
        self.desire_lines.emit(("text_dl", "Assigning demand"))
        self.desire_lines.emit(("job_size_dl", self.matrix.index.shape[0]))
        assigner = allOrNothing(self.matrix, self.graph, self.results)
        assigner.execute()
        self.report = assigner.report
        print(self.results.link_loads)
        self.desire_lines.emit(("text_dl", "Collecting results"))
        self.desire_lines.emit(("text_dl", "Building resulting layer"))
        features = []
        max_edges = len(edges)
        self.desire_lines.emit(("job_size_dl", max_edges))
        link_loads = self.results.get_load_results()
        for i, link_id in enumerate(link_loads.index):
            self.desire_lines.emit(("jobs_done_dl", i))
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
                        float(link_loads.data[c + "_ab"][i]),
                        float(link_loads.data[c + "_ba"][i]),
                        float(link_loads.data[c + "_tot"][i]),
                    ]
                )
            feature.setAttributes(attr)
            features.append(feature)
        _ = dlpr.addFeatures(features)
        self.result_layer = desireline_layer

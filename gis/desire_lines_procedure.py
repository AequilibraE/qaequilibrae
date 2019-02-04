"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Creating desire lines
 Purpose:    Implements procedure for Computing Desire lines based on a Delaunay Triangulation network on
             a separate thread

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-01
 Updated:    2017-06-25
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
from qgis.core import *
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtCore import *
import qgis
from qgis.core import *
import itertools
import numpy as np
import struct
import logging
from ..common_tools.auxiliary_functions import *
from aequilibrae.paths import Graph
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths.results import AssignmentResults
from collections import OrderedDict

from scipy.spatial import Delaunay

error = False

no_binary = False
from aequilibrae.paths import allOrNothing

#
# try:
#
# except:
#     no_binary = True

from ..common_tools import WorkerThread


class DesireLinesProcedure(WorkerThread):
    def __init__(self, parentThread, layer, id_field, matrix, matrix_hash, dl_type):
        # type: (int, int, int, AequilibraeMatrix, dict, str)-> None
        WorkerThread.__init__(self, parentThread)
        self.layer = layer
        self.id_field = id_field
        self.matrix = matrix
        self.dl_type = dl_type
        self.error = None
        self.matrix_hash = matrix_hash
        self.report = []
        self.logger = logging.getLogger('aequilibrae')
        self.nodes_to_indices = {matrix.index[x]: x for x in range(matrix.zones)}
        self.python_version = (8 * struct.calcsize("P"))

        if error:
            self.error = 'Scipy and/or Numpy not installed'
            self.report.append(self.error)
        self.procedure = "ASSIGNMENT"

    def doWork(self):
        if self.error is None:
            # In case we have only one class
            unnasigned = 0
            classes = self.matrix.matrix_view.shape[2]

            layer = get_vector_layer_by_name(self.layer)
            idx = layer.dataProvider().fieldNameIndex(self.id_field)
            feature_count = layer.featureCount()
            self.desire_lines.emit(('job_size_dl', feature_count))

            all_centroids = {}
            P = 0
            for feat in layer.getFeatures():
                P += 1
                self.desire_lines.emit(('jobs_done_dl', P))
                self.desire_lines.emit(('text_dl', "Loading Layer Features: " + str(P) + "/" + str(feature_count)))

                geom = feat.geometry()
                if geom is not None:
                    point = list(geom.centroid().asPoint())
                    centroid_id = feat.attributes()[idx]
                    all_centroids[centroid_id] = point

            # Creating resulting layer
            EPSG_code = int(layer.crs().authid().split(":")[1])

            desireline_layer = QgsVectorLayer("LineString?crs=epsg:" + str(EPSG_code), self.dl_type, "memory")
            dlpr = desireline_layer.dataProvider()
            fields = [QgsField("link_id", QVariant.Int),
                      QgsField("A_Node", QVariant.Int),
                      QgsField("B_Node", QVariant.Int),
                      QgsField("direct", QVariant.Int),
                      QgsField("distance", QVariant.Double)]
            for f in self.matrix.view_names:
                fields.extend([QgsField(f + '_ab', QVariant.Double),
                               QgsField(f + '_ba', QVariant.Double),
                               QgsField(f + '_tot', QVariant.Double)])

            dlpr.addAttributes(fields)
            desireline_layer.updateFields()

            if self.dl_type == "DesireLines":
                self.desire_lines.emit(('text_dl', "Creating Desire Lines"))
                self.desire_lines.emit(('job_size_dl', self.matrix.zones ** 2 / 2))

                desireline_link_id = 1
                q = 0
                all_features = []
                for i in range(self.matrix.zones):
                    a_node = self.matrix.index[i]
                    if a_node in all_centroids.keys():
                        if np.nansum(self.matrix.matrix_view[i, :, :]) + np.nansum(
                                self.matrix.matrix_view[:, i, :]) > 0:
                            columns_with_filled_cells = np.nonzero(np.nansum(self.matrix.matrix_view[i, :, :], axis=1))
                            for j in columns_with_filled_cells[0]:
                                if np.nansum(self.matrix.matrix_view[i, j, :]) + np.nansum(
                                        self.matrix.matrix_view[j, i, :]) > 0:
                                    b_node = self.matrix.index[j]
                                    if a_node in all_centroids.keys() and b_node in all_centroids.keys():
                                        a_point = all_centroids[a_node]
                                        a_point = QgsPointXY(a_point[0], a_point[1])
                                        b_point = all_centroids[b_node]
                                        b_point = QgsPointXY(b_point[0], b_point[1])
                                        dist = QgsGeometry().fromPointXY(a_point).distance(
                                            QgsGeometry().fromPointXY(b_point))
                                        feature = QgsFeature()
                                        feature.setGeometry(QgsGeometry.fromPolylineXY([a_point, b_point]))
                                        attrs = [desireline_link_id, int(a_node), int(b_node), 0, dist]
                                        for c in range(classes):
                                            attrs.extend([float(np.nansum(self.matrix.matrix_view[i, j, c])),
                                                          float(np.nansum(self.matrix.matrix_view[j, i, c])),
                                                          float(np.nansum(self.matrix.matrix_view[i, j, c])) +
                                                          float(np.nansum(self.matrix.matrix_view[j, i, c]))])

                                        feature.setAttributes(attrs)
                                        all_features.append(feature)
                                        desireline_link_id += 1
                                    else:
                                        tu = (a_node, b_node, np.nansum(self.matrix.matrix_view[i, j, :]),
                                              np.nansum(self.matrix.matrix_view[j, i, :]))
                                        self.report.append(
                                            'No centroids available to depict flow between node {0} and node'
                                            '{1}. Total AB flow was equal to {2} and total BA flow was '
                                            'equal to {3}'.format(*tu))
                                        unnasigned += np.nansum(self.matrix.matrix_view[i, j, :]) + \
                                                      np.nansum(self.matrix.matrix_view[j, i, :])
                    else:
                        tu = (a_node, np.nansum(self.matrix.matrix_view[i, :, :]))
                        self.report.append('No centroids available to depict flows from node {0} to all the others.'
                                           'Total flow from this zone is equal to {1}'.format(*tu))
                        unnasigned += np.nansum(self.matrix.matrix_view[i, :, :])

                    q += self.matrix.zones
                    self.desire_lines.emit(('jobs_done_dl', q))
                if unnasigned > 0:
                    self.report.append('Total non assigned flows (not counting intrazonals):' + str(unnasigned))

                if desireline_link_id > 1:
                    a = dlpr.addFeatures(all_features)
                    self.result_layer = desireline_layer
                else:
                    self.report.append('Nothing to show')

            elif self.dl_type == "DelaunayLines":

                self.desire_lines.emit(('text_dl', "Building Delaunay dataset"))
                points = []
                node_id_in_delaunay_results = {}
                i = 0
                self.desire_lines.emit(('job_size_dl', len(all_centroids)))
                for k, v in all_centroids.items():
                    self.desire_lines.emit(('jobs_done_dl', i))
                    points.append(v)
                    node_id_in_delaunay_results[i] = k
                    i += 1

                self.desire_lines.emit(('text_dl', "Computing Delaunay Triangles"))
                tri = Delaunay(np.array(points))

                # We process all the triangles to only get each edge once
                self.desire_lines.emit(('text_dl', "Building Delaunay Network: Collecting Edges"))
                edges = []
                if self.python_version == 32:
                    all_edges = tri.vertices
                else:
                    all_edges = tri.simplices

                self.desire_lines.emit(('job_size_dl', len(all_edges)))

                for j, triangle in enumerate(all_edges):
                    self.desire_lines.emit(('jobs_done_dl', j))
                    links = list(itertools.combinations(triangle, 2))
                    for i in links:
                        edges.append([min(i[0], i[1]), max(i[0], i[1])])

                self.desire_lines.emit(('text_dl', "Building Delaunay Network: Getting unique edges"))
                edges = OrderedDict((str(x), x) for x in edges).values()

                # Writing Delaunay layer
                self.desire_lines.emit(('text_dl', "Building Delaunay Network: Assembling Layer"))

                desireline_link_id = 1
                data = []
                dl_ids_on_links = {}
                self.desire_lines.emit(('job_size_dl', len(edges)))
                for j, edge in enumerate(edges):
                    self.desire_lines.emit(('jobs_done_dl', j))
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

                self.desire_lines.emit(('text_dl', "Building graph"))
                network = np.asarray(data)
                del data

                # types for the network
                self.graph = Graph()
                itype = self.graph.default_types('int')
                ftype = self.graph.default_types('float')
                all_types = [itype, itype, itype, ftype, ftype, np.int8]
                all_titles = ['link_id', 'a_node', 'b_node', 'distance_ab', 'distance_ba', 'direction']
                dt = [(t, d) for t, d in zip(all_titles, all_types)]
                self.graph.network = np.zeros(network.shape[0], dtype=dt)

                for k, t in enumerate(dt):
                    self.graph.network[t[0]] = network[:, k].astype(t[1])
                del network

                self.graph.type_loaded = 'NETWORK'
                self.graph.status = 'OK'
                self.graph.network_ok = True
                self.graph.prepare_graph(self.matrix.index.astype(np.int64))
                self.graph.set_graph(cost_field='distance', skim_fields=False, block_centroid_flows=False)

                self.results = AssignmentResults()
                self.results.prepare(self.graph, self.matrix)
                self.desire_lines.emit(('text_dl', "Assigning demand"))
                self.desire_lines.emit(('job_size_dl', self.matrix.index.shape[0]))

                assigner = allOrNothing(self.matrix, self.graph, self.results)
                assigner.execute()
                self.report = assigner.report
                print(self.results.link_loads)
                self.desire_lines.emit(('text_dl', "Collecting results"))
                self.desire_lines.emit(('text_dl', "Building resulting layer"))
                features = []
                max_edges = len(edges)
                self.desire_lines.emit(('job_size_dl', max_edges))
                link_loads = self.results.save_to_disk()
                for i, link_id in enumerate(link_loads.index):
                    self.desire_lines.emit(('jobs_done_dl', i))
                    a_node, b_node, direct, dist = dl_ids_on_links[link_id]

                    attr = [int(link_id), a_node, b_node, direct, dist]

                    a_point = all_centroids[a_node]
                    a_point = QgsPointXY(a_point[0], a_point[1])
                    b_point = all_centroids[b_node]
                    b_point = QgsPointXY(b_point[0], b_point[1])

                    feature = QgsFeature()
                    feature.setGeometry(QgsGeometry.fromPolylineXY([a_point, b_point]))

                    for c in self.matrix.view_names:
                        attr.extend([float(link_loads.data[c + '_ab'][i]),
                                     float(link_loads.data[c + '_ba'][i]),
                                     float(link_loads.data[c + '_tot'][i])])
                    feature.setAttributes(attr)
                    features.append(feature)
                a = dlpr.addFeatures(features)
                self.result_layer = desireline_layer

        self.desire_lines.emit(('finished_desire_lines_procedure', 0))

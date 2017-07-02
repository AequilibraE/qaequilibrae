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
 Updated:    2017-05-07
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
import qgis
from qgis.core import *
from PyQt4.QtCore import *
import itertools
import numpy as np
import struct
from ..common_tools.auxiliary_functions import *
from aequilibrae.paths import Graph
from aequilibrae.paths.results import AssignmentResults

error = False
try:
    from scipy.spatial import Delaunay
except:
    error = True

no_binary = False
try:
    from aequilibrae.paths import all_or_nothing
    #from aequilibrae.paths import MultiThreadedAoN, one_to_all
except:
    no_binary = True

from ..common_tools import WorkerThread

class DesireLinesProcedure(WorkerThread):
    def __init__(self, parentThread, layer, id_field, matrix, matrix_hash, dl_type):
        WorkerThread.__init__(self, parentThread)
        self.layer = layer
        self.id_field = id_field
        self.matrix = matrix
        self.dl_type = dl_type
        self.error = None
        self.matrix_hash = matrix_hash
        self.not_loaded = []
        self.report = []
        self.python_version = (8 * struct.calcsize("P"))

        if error:
            self.error = 'Scipy and/or Numpy not installed'
        self.procedure = "ASSIGNMENT"

    def doWork(self):
        if self.error is None:
            layer = get_vector_layer_by_name(self.layer)
            idx = layer.fieldNameIndex(self.id_field)
            matrix = self.matrix

            matrix_nodes = max(self.matrix_hash.values()) + 1
            featcount = layer.featureCount()
            self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), (0, featcount))

            all_centroids = {}
            P = 0
            for feat in layer.getFeatures():
                P += 1
                self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, int(P)))
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Loading Layer Features: " + str(P) + "/" + str(featcount)))

                geom = feat.geometry()
                if geom is not None:
                    point = list(geom.centroid().asPoint())
                    centroid_id = feat.attributes()[idx]
                    all_centroids[centroid_id] = point

                    if centroid_id not in self.matrix_hash.keys():
                        self.matrix_hash[centroid_id] = matrix_nodes
                        matrix_nodes += 1
            reverse_hash = {v: k for k, v in self.matrix_hash.iteritems()}

            #Creating resulting layer
            EPSG_code = int(layer.crs().authid().split(":")[1])

            desireline_layer = QgsVectorLayer("LineString?crs=epsg:" + str(EPSG_code), self.dl_type, "memory")
            dlpr = desireline_layer.dataProvider()
            dlpr.addAttributes([QgsField("link_id", QVariant.Int),
                              QgsField("A_Node", QVariant.Int),
                              QgsField("B_Node", QVariant.Int),
                              QgsField("direct", QVariant.Int),
                              QgsField("length",  QVariant.Double),
                              QgsField("AB_FLOW",  QVariant.Double),
                              QgsField("BA_FLOW",  QVariant.Double),
                              QgsField("TOT_FLOW",  QVariant.Double)])
            desireline_layer.updateFields()


            if self.dl_type == "DesireLines":
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Creating Desire Lines"))
                self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), (0, self.matrix.shape[0]*self.matrix.shape[1]/2))

                desireline_link_id = 1
                q = 0
                all_features = []
                for i in range(self.matrix.shape[0]):
                    if np.sum(self.matrix[i, :]) > 0:
                        a_node = reverse_hash[i]
                        for j in xrange(i + 1, self.matrix.shape[1]):
                            q += 1
                            b_node = reverse_hash[j]
                            self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, q))
                            if self.matrix[i, j] + self.matrix[j, i] > 0:
                                if a_node in all_centroids.keys() and b_node in all_centroids.keys():
                                    a_point = all_centroids[a_node]
                                    a_point = QgsPoint(a_point[0], a_point[1])
                                    b_point = all_centroids[b_node]
                                    b_point = QgsPoint(b_point[0], b_point[1])
                                    dist = QgsGeometry().fromPoint(a_point).distance(QgsGeometry().fromPoint(b_point))
                                    feature = QgsFeature()
                                    feature.setGeometry(QgsGeometry.fromPolyline([a_point, b_point]))
                                    feature.setAttributes([desireline_link_id, int(a_node), int(b_node), 0, dist,
                                                           float(self.matrix[i ,j]), float(self.matrix[j, i]),
                                                           float(self.matrix[i, j] + self.matrix[j, i])])
                                    all_features.append(feature)
                                    desireline_link_id += 1
                                else:
                                    tu = (a_node, b_node, self.matrix[i, j], self.matrix[j, i])
                                    self.not_loaded.append('No centroids available to depict flow between node {0} and node {1}. AB flow was equal to {2} and BA flow was equal to {3}'.format(*tu))
                    else:
                        q += self.matrix.shape[1]
                        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, q))


                if desireline_link_id > 1:
                    a = dlpr.addFeatures(all_features)
                    self.result_layer = desireline_layer
                else:
                    self.error = 'Nothing to show'

            elif self.dl_type == "DelaunayLines":

                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0, "Computing Delaunay Triangles"))
                points = []
                seccond_relation ={}
                i = 0
                for k, v in all_centroids.iteritems():
                    points.append(v)
                    seccond_relation[i] = k
                    i += 1

                tri = Delaunay(np.array(points))

                #We process all the triangles to only get each edge once
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0, "Building Delaunay Network: Collecting Edges"))
                edges = []
                if self.python_version == 32:
                    all_edges = tri.vertices
                else:
                    all_edges = tri.simplices

                for triangle in all_edges:
                    links = list(itertools.combinations(triangle, 2))
                    for i in links:
                        l= [min(i[0],i[1]), max(i[0],i[1])]
                        if l not in edges:
                            edges.append(l)

                #Writing Delaunay layer
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0, "Building Delaunay Network: Assembling Layer"))

                desireline_link_id = 1
                data = []
                dl_link_ids = {}
                for edge in edges:
                        a_node = seccond_relation[edge[0]]
                        a_point = all_centroids[a_node]
                        a_point = QgsPoint(a_point[0], a_point[1])
                        b_node = seccond_relation[edge[1]]
                        b_point = all_centroids[b_node]
                        b_point = QgsPoint(b_point[0], b_point[1])
                        dist = QgsGeometry().fromPoint(a_point).distance(QgsGeometry().fromPoint(b_point))
                        line = []
                        line.append(desireline_link_id)
                        line.append(self.matrix_hash[a_node])
                        line.append(self.matrix_hash[b_node])
                        line.append(dist)
                        line.append(dist)
                        line.append(0)
                        data.append(line)
                        if a_node not in dl_link_ids.keys():
                            dl_link_ids[a_node] = {}
                        dl_link_ids[a_node][b_node] = desireline_link_id
                        desireline_link_id += 1

                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0, "Building graph"))
                network = np.asarray(data)
                del data

                #types for the network
                all_types = [np.int64, np.int64, np.int64, np.float64, np.float64, np.int64]
                all_titles = ['link_id', 'a_node', 'b_node', 'length_ab', 'length_ba', 'direction']
                dt = [(t, d) for t, d in zip(all_titles, all_types)]

                self.graph = Graph()
                self.graph.network = np.zeros(network.shape[0], dtype=dt)

                for k, t in enumerate(dt):
                    self.graph.network[t[0]] = network[:, k].astype(t[1])
                del network

                self.graph.type_loaded = 'NETWORK'
                self.graph.status = 'OK'
                self.graph.network_ok = True
                self.graph.prepare_graph()

                self.graph.set_graph(matrix_nodes, cost_field='length', block_centroid_flows=False)
                self.results = AssignmentResults()
                self.results.prepare(self.graph)
                # self.results.set_cores(1)

                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0, "Assigning demand"))
                # Do the assignment
                #self.all_or_nothing(self.matrix, self.graph, self.results)
                self.report = all_or_nothing(self.matrix, self.graph, self.results)

                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0, "Collecting results"))
                f = self.results.link_loads

                link_loads = np.zeros((f.shape[0] + 1, 2))
                self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), (0, f.shape[0] - 1))
                for i in range(f.shape[0] - 1):
                    self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, i))
                    direction = self.graph.graph['direction'][i]
                    link_id = self.graph.graph['link_id'][i]
                    flow = f[i]
                    if direction == 1:
                        link_loads[link_id, 0] = flow
                    else:
                        link_loads[link_id, 1] = flow

                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0, "Building resulting layer"))
                features = []
                max_edges = len(edges)
                self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), (0, max_edges))

                for i, edge in enumerate(edges):
                    self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, i))
                    a_node = seccond_relation[edge[0]]
                    a_point = all_centroids[a_node]
                    a_point = QgsPoint(a_point[0], a_point[1])
                    b_node = seccond_relation[edge[1]]
                    b_point = all_centroids[b_node]
                    b_point = QgsPoint(b_point[0], b_point[1])
                    dist = QgsGeometry().fromPoint(a_point).distance(QgsGeometry().fromPoint(b_point))

                    feature = QgsFeature()
                    feature.setGeometry(QgsGeometry.fromPolyline([a_point, b_point]))
                    desireline_link_id = dl_link_ids[a_node][b_node]
                    feature.setAttributes([desireline_link_id, a_node, b_node, 0, dist,
                                           float(link_loads[desireline_link_id, 0]), float(link_loads[desireline_link_id, 1]),
                                           float(link_loads[desireline_link_id, 0] + link_loads[desireline_link_id, 1])])
                    features.append(feature)
                a = dlpr.addFeatures(features)
                self.result_layer = desireline_layer

        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), True)
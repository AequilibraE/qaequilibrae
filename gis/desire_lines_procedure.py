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
            self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), (0,featcount))

            P = 0
            points = []
            point_ids = []
            for feat in layer.getFeatures():
                P += 1
                self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0,int(P)))
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Loading Layer Features: " + str(P) + "/" + str(featcount)))

                geom = feat.geometry()
                if geom is not None:
                    point =list(geom.centroid().asPoint())
                    points.append(point)
                    point_ids.append(feat.attributes()[idx])

            points = np.array(points)

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

                #We create the dictionary with point information
                all_points={}
                point_ids = np.array(point_ids).astype(np.int)
                for i in range(point_ids.shape[0]):
                    all_points[point_ids[i]]=points[i]

                # We are assuming that the matrix is square here
                reverse_hash = {v: k for k, v in self.matrix_hash.iteritems()}
                desireline_link_id = 1
                q = 0
                all_features = []
                for i in range(self.matrix.shape[0]):
                    if np.sum(self.matrix[i, :]) > 0:
                        a_node = reverse_hash[i]
                        for j in xrange(i + 1, self.matrix.shape[1]):
                            q += 1
                            self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, q))
                            if self.matrix[i,j]+self.matrix[j,i] > 0:
                                b_node = reverse_hash[j]
                                if a_node in all_points.keys() and b_node in all_points.keys():
                                    a_point = QgsPoint(all_points[a_node][0], all_points[a_node][1])
                                    b_point = QgsPoint(all_points[b_node][0], all_points[b_node][1])
                                    dist = QgsGeometry().fromPoint(a_point).distance(QgsGeometry().fromPoint(b_point))
                                    feature = QgsFeature()
                                    feature.setGeometry(QgsGeometry.fromPolyline([a_point, b_point]))
                                    feature.setAttributes([desireline_link_id, a_node, b_node, 0, dist,
                                                           float(self.matrix[i ,j]), float(self.matrix[j, i]),
                                                           float(self.matrix[i, j] + self.matrix[j, i])])
                                    all_features.append(feature)
                                    desireline_link_id += 1
                                else:
                                    tu = (a_node, b_node, self.matrix[i, j], self.matrix[j, i])
                                    self.not_loaded.append('Flows between node {0} and node {1} could not be loaded. AB flow was equal to {2} and BA flow was equal to {3}'.format(*tu))
                if desireline_link_id > 1:
                    a = dlpr.addFeatures(all_features)
                    self.result_layer = desireline_layer
                else:
                    self.error = 'Nothing to show'

            elif self.dl_type == "DelaunayLines":
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Computing Delaunay Triangles"))
                tri = Delaunay(points)

                #We process all the triangles to only get each edge once
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Building Delaunay Network: Collecting Edges"))
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
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Building Delaunay Network: Assembling Layer"))

                desireline_link_id = 1
                data = []
                for edge in edges:
                        a_node = edge[0]
                        a_point = QgsPoint(points[a_node][0], points[a_node][1])
                        b_node = edge[1]
                        b_point = QgsPoint(points[b_node][0], points[b_node][1])
                        dist = QgsGeometry().fromPoint(a_point).distance(QgsGeometry().fromPoint(b_point))
                        line = []
                        line.append(desireline_link_id)

                        if point_ids[a_node] not in self.matrix_hash.keys():
                            self.matrix_hash[point_ids[a_node]] = matrix_nodes
                            matrix_nodes += 1

                        if point_ids[b_node] not in self.matrix_hash.keys():
                            self.matrix_hash[point_ids[b_node]] = matrix_nodes
                            matrix_nodes += 1

                        line.append(self.matrix_hash[point_ids[a_node]])
                        line.append(self.matrix_hash[point_ids[b_node]])
                        line.append(dist)
                        line.append(dist)
                        line.append(0)
                        data.append(line)
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
                self.graph.save_to_disk('E:/test.aeg')
                self.results = AssignmentResults()
                self.results.prepare(self.graph)
                self.results.set_cores(1)

                # Do the assignment
                #self.all_or_nothing(self.matrix, self.graph, self.results)
                all_or_nothing(self.matrix, self.graph, self.results)

                f = self.results.link_loads
                link_loads = np.zeros((f.shape[0]+1, 2))
                for i in range(f.shape[0]-1):
                    direction = self.graph.graph['direction'][i]
                    link_id = self.graph.graph['link_id'][i]
                    flow = f[i]
                    if direction == 1:
                        link_loads[link_id, 0] = flow
                    else:
                        link_loads[link_id, 1] = flow

                desireline_link_id = 1
                features = []
                for edge in edges:
                    a_node = edge[0]
                    a_point = QgsPoint(points[a_node][0], points[a_node][1])
                    b_node = edge[1]
                    b_point = QgsPoint(points[b_node][0], points[b_node][1])
                    dist = QgsGeometry().fromPoint(a_point).distance(QgsGeometry().fromPoint(b_point))
                    feature = QgsFeature()
                    feature.setGeometry(QgsGeometry.fromPolyline([a_point, b_point]))
                    feature.setAttributes([desireline_link_id, point_ids[a_node], point_ids[b_node], 0, dist,
                                           float(link_loads[desireline_link_id, 0]), float(link_loads[desireline_link_id, 1]),
                                           float(link_loads[desireline_link_id, 0] + link_loads[desireline_link_id, 1])])
                    features.append(feature)
                    desireline_link_id += 1
                a = dlpr.addFeatures(features)
                self.result_layer = desireline_layer

        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), True)

    # def all_or_nothing(self, matrix, graph, results):
    #     aux_res = MultiThreadedAoN()
    #     aux_res.prepare(graph, results)
    #     for O in range(matrix.shape[0]):
    #         one_to_all(O, matrix[O, :], graph, results, aux_res, 0)
    #     results.link_loads = np.sum(aux_res.temp_link_loads, axis=1)

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
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
import qgis
from qgis.core import *
from PyQt4.QtCore import *
import itertools
import numpy as np

from auxiliary_functions import *
from aequilibrae.paths import Graph
from aequilibrae.paths.results import AssignmentResults
from aequilibrae.paths import all_or_nothing

from aequilibrae.paths import one_to_all, reblocks_matrix

error = False
try:
    from scipy.spatial import Delaunay
except:
    error = True

from worker_thread import WorkerThread

class DesireLinesProcedure(WorkerThread):
    def __init__(self, parentThread, layer, id_field, matrix, dl_type):
        WorkerThread.__init__(self, parentThread)
        self.layer = layer
        self.id_field = id_field
        self.matrix = matrix
        self.dl_type = dl_type
        self.error = None
        if error:
            self.error = 'Scipy and/or Numpy not installed'
        self.procedure = "ASSIGNMENT"

    def doWork(self):
        if self.error is None:
            layer = get_vector_layer_by_name(self.layer)
            idx = layer.fieldNameIndex(self.id_field)
            matrix = self.matrix

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
            self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, featcount))

            self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Preparing consistency check Matrix Vs. Zoning layer"))

            vector1 = np.nonzero(np.sum(matrix, axis=0))[0]
            vector2 = np.nonzero(np.sum(matrix, axis=1))[0]
            nonzero = np.hstack((vector1,vector2))

            self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0,nonzero.shape[0]))
            for i, zone in enumerate(nonzero):
                if zone not in point_ids:
                    self.error = 'Zone ' + str(zone) + ' with positive flow not in zoning file'
                    break
                self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), (0,i+1))
            self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, nonzero.shape[0]))

        if self.error is None:

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

                # We are assuming that the matrix is square here. Maybe we could add more general code layer
                desireline_link_id = 1
                q = 0
                all_features = []
                for i in range(self.matrix.shape[0]):
                    for j in xrange(i+1,self.matrix.shape[1]):
                        q += 1
                        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), (0, q))
                        if self.matrix[i,j]+self.matrix[j,i] > 0:
                            a_node = i
                            a_point = QgsPoint(all_points[a_node][0], all_points[a_node][1])
                            b_node = j
                            b_point = QgsPoint(all_points[b_node][0], all_points[b_node][1])
                            dist = QgsGeometry().fromPoint(a_point).distance(QgsGeometry().fromPoint(b_point))
                            feature = QgsFeature()
                            feature.setGeometry(QgsGeometry.fromPolyline([a_point, b_point]))
                            feature.setAttributes([desireline_link_id, a_node, b_node, 0, dist,
                                                   float(self.matrix[i ,j]), float(self.matrix[j, i]),
                                                   float(self.matrix[i, j] + self.matrix[j, i])])
                            all_features.append(feature)

                            desireline_link_id += 1
                a = dlpr.addFeatures(all_features)
                self.result_layer = desireline_layer

            elif self.dl_type == "DelaunayLines":
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Computing Delaunay Triangles"))
                tri = Delaunay(points)

                #We process all the triangles to only get each edge once
                self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), (0,"Building Delaunay Network: Collecting Edges"))
                edges = []
                for triangle in tri.simplices:
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
                        line.append(point_ids[a_node])
                        line.append(point_ids[b_node])
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

                # Here we transform the network to go from node 1 to N
                max_node = max(np.max(self.graph.network['a_node']), np.max(self.graph.network['b_node']))
                max_node = max(max_node, self.matrix.shape[0], self.matrix.shape[1]) + 1
                self.hash = np.zeros(max_node, np.int)

                # Checks if any zone from the matrix is not present in the areas/node layer
                t1 = np.sum(self.matrix, axis=0)
                t2 = np.sum(self.matrix, axis=1)

                if t1.shape[0] > t2.shape[0]:
                    t2.resize(t1.shape)
                elif t2.shape[0] > t1.shape[0]:
                    t1.resize(t2.shape)
                totals = t1 + t2

                all_nodes = np.bincount(self.graph.network['a_node'])
                for i in range(totals.shape[0]):
                    if totals[i]:
                        if not all_nodes[i]:
                            qgis.utils.iface.messageBar().pushMessage("Matrix has demand for zones that do not exist "
                                                                      "in the zones/nodes provided. Demand for those"
                                                                      "ones were ignored. e.g. " +  str(i),'', level=3)
                            break

                h = 1
                for i in range(self.graph.network.shape[0]):
                    a_node = self.graph.network['a_node'][i]
                    if self.hash[a_node] == 0:
                        self.hash[a_node] = h
                        h += 1

                    b_node = self.graph.network['b_node'][i]
                    if self.hash[b_node] == 0:
                        self.hash[b_node] = h
                        h += 1

                    self.graph.network['a_node'][i] = self.hash[a_node]
                    self.graph.network['b_node'][i] = self.hash[b_node]
                # End of network transformation

                #Now we transform the matrix appropriately
                self.matrix = reblocks_matrix(self.matrix, self.hash, h)

                self.graph.type_loaded = 'NETWORK'
                self.graph.status = 'OK'
                self.graph.network_ok = True
                self.graph.prepare_graph()

                self.graph.set_graph(h-1, cost_field='length', block_centroid_flows=False)
                self.results = AssignmentResults()
                self.results.prepare(self.graph)
                self.results.set_cores(1)

                for O in range(self.matrix.shape[0]):
                    a = self.matrix[O, :]
                    if np.sum(a) > 0:
                        one_to_all(O, a, self.graph, self.results, 0, no_gil=False)

                #all_or_nothing(self.matrix, self.graph, self.results)

                f = self.results.link_loads[:,0]
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
                    a = dlpr.addFeatures([feature])
                    desireline_link_id += 1
                self.result_layer = desireline_layer

        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), True)


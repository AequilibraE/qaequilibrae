"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Adding centroid connectors procedure
 Purpose:    Executes centroid addition procedure in a separate thread

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    21/12/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from qgis.PyQt.QtCore import *
from ..common_tools.auxiliary_functions import *

from ..common_tools.global_parameters import *
from ..common_tools import WorkerThread


class AddsConnectorsProcedure(WorkerThread):
    def __init__(self, parentThread, node_layer_name, link_layer_name, centroid_layer_name, node_ids, centroids_ids,
                 max_length, max_connectors, new_line_layer_name, new_node_layer_name, selection_only):
        WorkerThread.__init__(self, parentThread)
        self.link_layer_name = link_layer_name
        self.node_layer_name = node_layer_name
        self.centroid_layer_name = centroid_layer_name
        self.node_ids = node_ids
        self.centroids_ids = centroids_ids
        if max_length is None:
            max_length = 1000000000000
        self.max_length = max_length
        self.max_connectors = max_connectors
        self.new_line_layer_name = new_line_layer_name
        self.new_node_layer_name = new_node_layer_name
        self.selection_only = selection_only
        self.error = None

    def doWork(self):
        max_connectors = self.max_connectors

        nodes = get_vector_layer_by_name(self.node_layer_name)
        centroids = get_vector_layer_by_name(self.centroid_layer_name)
        links = get_vector_layer_by_name(self.link_layer_name)

        self.ProgressText.emit("Duplicating layers")
        self.ProgressMaxValue.emit(2)
        # We create the new line layer
        new_line_layer = self.duplicate_layer(links, 'LineString', self.new_line_layer_name)

        # Create new node layer
        self.ProgressValue.emit(1)
        new_node_layer = self.duplicate_layer(nodes, 'Point', self.new_node_layer_name)

        # Now we start to set the field for writing the new data
        idx = nodes.dataProvider().fieldNameIndex(self.node_ids)
        idx2 = centroids.dataProvider().fieldNameIndex(self.centroids_ids)
        anode = links.dataProvider().fieldNameIndex("A_NODE")
        bnode = links.dataProvider().fieldNameIndex("B_NODE")
        ids=[]

        if anode < 0 or bnode < 0:
            self.error = 'Line layer does not have A_Node and B_Node fields. Run network preparation first'
            return None

        # Create the spatial index with nodes
        self.ProgressValue.emit(0)
        self.ProgressText.emit("Creating Spatial Index")
        index = QgsSpatialIndex()
        MyFeatures = nodes.getFeatures()
        featcount = nodes.featureCount()
        if self.selection_only:
            MyFeatures = nodes.selectedFeatures()
            featcount = nodes.selectedFeatureCount()

        self.ProgressMaxValue.emit(featcount)
        P = 0
        for feat in MyFeatures:
            self.ProgressValue.emit(P)
            a = index.insertFeature(feat)
            i_d = feat.attributes()[idx]
            if i_d in ids:
                self.error = "ID " + str(i_d) + ' is non unique in your selected field'
                return None
            if i_d<0:
                self.error = "Negative node ID in your selected field"
                return None
            ids.append(i_d)
            P += 1

        P = 0
        added_centroids = []
        added_nodes = []
        featcount = centroids.featureCount()
        self.ProgressMaxValue.emit(featcount)
        self.ProgressValue.emit(0)
        self.ProgressText.emit("Creating centroid connectors")

        for feat in centroids.getFeatures():
            P += 1
            self.ProgressValue.emit(int(P))
            nearest = index.nearestNeighbor(feat.geometry().asPoint(), max_connectors)

            lon1, lat1 = feat.geometry().asPoint()
            found = 0
            for i in range(max_connectors):
                fid = nearest[i]
                nfeat = nodes.getFeatures(QgsFeatureRequest(fid)).__next__()
                lon2, lat2 = nfeat.geometry().asPoint()
                dist = haversine(lon1, lat1, lon2, lat2)
                if dist <= self.max_length:
                    found += 1
                    line = QgsGeometry.fromPolylineXY([feat.geometry().asPoint(), nfeat.geometry().asPoint()])
                    seg = QgsFeature(links.fields())
                    a = seg.setGeometry(line)
                    a = seg.setAttribute(anode, feat.attributes()[idx2])
                    a = seg.setAttribute(bnode, nfeat.attributes()[idx])
                    a = added_centroids.append(seg)
            if found > 0:
                seg = QgsFeature(nodes.fields())
                a = seg.setGeometry(feat.geometry())
                a = seg.setAttribute(idx, feat.attributes()[idx2])
                a = added_nodes.append(seg)
        if len(added_centroids) > 0:
            a = new_line_layer.dataProvider().addFeatures(added_centroids)
            a = new_node_layer.dataProvider().addFeatures(added_nodes)

        self.ProgressText.emit("Saving new line layer")
        new_line_layer.commitChanges()
        self.new_node_layer = new_node_layer

        self.ProgressText.emit("Saving new node layer")
        new_node_layer.commitChanges()
        self.new_line_layer = new_line_layer

        self.ProgressText.emit("DONE")

    def duplicate_layer(self, original_layer, layer_type, layer_name):
        epsg_code = int(original_layer.crs().authid().split(":")[1])
        feats = [feat for feat in original_layer.getFeatures()]
        duplicate_layer = QgsVectorLayer(layer_type + "?crs=epsg:" + str(epsg_code), layer_name, "memory")
        new_layer_data = duplicate_layer.dataProvider()
        attr = original_layer.dataProvider().fields().toList()
        new_layer_data.addAttributes(attr)
        duplicate_layer.updateFields()
        new_layer_data.addFeatures(feats)
        del feats
        return duplicate_layer
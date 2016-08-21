"""
/***************************************************************************
 AequilibraE - www.AequilibraE.com

    Name:        Dialog for computing and displaying shortest paths based on clicks on the map
                              -------------------
        begin                : 2016-07-30
        copyright            : AequilibraE developers 2016
        Original Author: Pedro Camargo (c@margo.co)
        Contributors:
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""

from qgis.core import *
import qgis
from qgis.gui import QgsMapToolEmitPoint
from PyQt4 import QtGui
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4
from random import randint

import sys
import os
from functools import partial
from auxiliary_functions import *
from global_parameters import *
from point_tool import PointTool
from aequilibrae.paths import Graph
from aequilibrae.paths.results import PathResults
from aequilibrae.paths import path_computation

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\\forms\\")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\\aequilibrae\\")

# Inside def setupUi
# self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

# from show_shortest_path_procedure import *
from ui_compute_path import *

class ShortestPathDialog(QtGui.QDialog, Ui_compute_path):
    def __init__(self, iface):
        QDialog.__init__(self)
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        self.iface = iface
        self.setupUi(self)
        self.field_types = {}
        self.centroids = None
        self.node_layer = None
        self.line_layer = None
        self.index = None
        self.clickTool = PointTool(self.iface.mapCanvas())
        self.res = PathResults()
        self.link_features = None
        # For adding skims
        self.load_graph_from_file.clicked.connect(self.loaded_new_graph_from_file)

        self.cb_node_layer.currentIndexChanged.connect(partial(self.load_fields_to_ComboBoxes, self.cb_node_layer,
                                                               self.cb_data_field, True))

        self.cb_link_layer.currentIndexChanged.connect(partial(self.load_fields_to_ComboBoxes, self.cb_link_layer,
                                                               self.cb_link_id_field, False))

        self.cb_link_id_field.currentIndexChanged.connect(self.clear_memory_layer)

        self.from_but.clicked.connect(self.search_for_point_from)
        self.to_but.clicked.connect(self.search_for_point_to)

        self.do_dist_matrix.clicked.connect(self.produces_path)


        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if layer.wkbType() in point_types:
                self.cb_node_layer.addItem(layer.name())

            if layer.wkbType() in line_types:
                self.cb_link_layer.addItem(layer.name())

        # loads default path from parameters
        self.path = standard_path()

    def clear_memory_layer(self):
        self.link_features = None
    def check_parameters(self):
        if self.cb_node_layer.currentIndex() >= 0 and self.cb_data_field.currentIndex() >= 0:
            return True
        else:
            qgis.utils.iface.messageBar().pushMessage("Wrong settings", "Please select node layer and ID field", level=3,
                                                      duration=3)
            return False

    def search_for_point_from(self):
        if self.check_parameters():
            self.iface.mapCanvas().setMapTool(self.clickTool)
            QObject.connect(self.clickTool, SIGNAL("clicked"), self.fill_path_from)
            self.from_but.setEnabled(False)

    def search_for_point_to(self):
        if self.check_parameters():
            self.iface.mapCanvas().setMapTool(self.clickTool)
            QObject.connect(self.clickTool, SIGNAL("clicked"), self.fill_path_to)
            self.to_but.setEnabled(False)

    def fill_path_to(self):
        self.to_but.setEnabled(True)
        self.toNode = self.find_point()
        self.path_to.setText(str(self.toNode))

    def fill_path_from(self):
        self.from_but.setEnabled(True)
        self.fromNode = self.find_point()
        self.path_from.setText(str(self.fromNode))

    def find_point(self):
        try:
            point = self.clickTool.point
            nearest = self.index.nearestNeighbor(point, 1)
            self.iface.mapCanvas().setMapTool(None)
            self.clickTool = PointTool(self.iface.mapCanvas())
            node_id = self.node_keys[nearest[0]]

            index_field = self.node_fields.index(self.cb_data_field.currentText())
            node_actual_id = node_id[index_field]
            return node_actual_id
        except:
            pass

    def load_fields_to_ComboBoxes(self, combobox, combofield, node_layer):
        combofield.clear()
        if combobox.currentIndex() >= 0:
            layer = getVectorLayerByName(combobox.currentText())
            for field in layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    combofield.addItem(field.name())
            if node_layer:
                # We create the spatial index used to associate the click to the network nodes
                self.node_fields = [field.name() for field in layer.pendingFields()]
                self.node_keys = {}
                self.index = QgsSpatialIndex()
                for feature in layer.getFeatures():
                    self.index.insertFeature(feature)
                    self.node_keys[feature.id()] = feature.attributes()
                self.node_layer = layer
            else:
                self.line_layer = layer

    def loaded_new_graph_from_file(self):
        file_types = "AequilibraE graph(*.aeg)"

        if len(self.graph_file_name.text()) == 0:
            newname = QFileDialog.getOpenFileName(None, 'Result file', self.path, file_types)
        else:
            newname = QFileDialog.getOpenFileName(None, 'Result file', self.graph_file_name.text(), file_types)
        self.cb_minimizing.clear()
        self.all_centroids.setText('')
        self.block_paths.setChecked(False)
        if newname != None:
            self.graph_file_name.setText(newname)
            self.graph = Graph()
            self.graph.load_from_disk(newname)
            self.res.prepare(self.graph)

            self.all_centroids.setText(str(self.graph.centroids))
            if self.graph.block_centroid_flows:
                self.block_paths.setChecked(True)
            graph_fields = list(self.graph.graph.dtype.names)
            self.skimmeable_fields = [x for x in graph_fields if
                                      x not in ['link_id', 'a_node', 'b_node', 'direction', 'id', ]]

            for q in self.skimmeable_fields:
                self.cb_minimizing.addItem(q)

    def produces_path(self):
        if len(self.path_from.text()) > 0 and len(self.path_to.text())> 0:
            self.res.reset()
            path_computation(int(self.path_from.text()), int(self.path_to.text()), self.graph, self.res)

            if self.res.path is not None:
                ## If you want to do selections instead of new layers, this is how to do it

                # f = self.cb_link_id_field.currentText()
                # t = ''
                # for k in self.res.path[:-1]:
                #     t = t + f + "=" + str(k) + ' or '
                # t = t + f + "=" + str(self.res.path[-1])
                # expr = QgsExpression(t)
                # it = self.line_layer.getFeatures(QgsFeatureRequest(expr))
                #
                # ids = [i.id() for i in it]
                # self.line_layer.setSelectedFeatures(ids)

                # If you want to create new layers
                # This way is MUCH faster
                if self.link_features is None:
                    idx = self.line_layer.fieldNameIndex(self.cb_link_id_field.currentText())
                    self.link_features = {}
                    for feat in self.line_layer.getFeatures():
                        link_id = feat.attributes()[idx]
                        self.link_features[link_id] = feat

                crs = self.line_layer.dataProvider().crs().authid()
                vl = QgsVectorLayer("LineString?crs={}".format(crs), self.path_from.text() + " to " + self.path_to.text(), "memory")
                pr = vl.dataProvider()

                # add fields
                pr.addAttributes(self.line_layer.dataProvider().fields())
                vl.updateFields()  # tell the vector layer to fetch changes from the provider

                # add a feature
                all_links=[]
                for k in self.res.path:
                    fet = self.link_features[k]
                    all_links.append(fet)

                # add all links to the temp layer
                pr.addFeatures(all_links)

                # add layer to the map
                QgsMapLayerRegistry.instance().addMapLayer(vl)

                # format the layer with a thick line
                registry = QgsSymbolLayerV2Registry.instance()
                lineMeta = registry.symbolLayerMetadata("SimpleLine")
                symbol = QgsLineSymbolV2()
                lineLayer = lineMeta.createSymbolLayer({'width': '1', 'color': self.random_rgb(), 'offset': '0', 'penstyle': 'solid',
                                                    'use_custom_dash': '0', 'joinstyle': 'bevel', 'capstyle': 'square'})
                symbol.deleteSymbolLayer(0)
                symbol.appendSymbolLayer(lineLayer)
                renderer = QgsSingleSymbolRendererV2(symbol)
                vl.setRendererV2(renderer)
                qgis.utils.iface.mapCanvas().refresh()

            else:
                qgis.utils.iface.messageBar().pushMessage("No path between " + self.path_from.text() + ' and ' + self.path_to.text(), '', level=3)

    def random_rgb(self):
        rgb = ''
        for i in range(3):
            rgb = rgb + str(randint(0, 255)) + ','
        return rgb[:-1]

    def ExitProcedure(self):
        self.close()
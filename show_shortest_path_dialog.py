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

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/")

# Inside def setupUi
# self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

from ui_compute_path import *
from load_graph_layer_setting_dialog import LoadGraphLayerSettingDialog

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
        self.node_keys = None
        self.node_fields = None
        self.index = None
        self.matrix = None
        self.clickTool = PointTool(self.iface.mapCanvas())
        self.path = standard_path()
        self.node_id = None

        self.res = PathResults()
        self.link_features = None

        self.do_dist_matrix.setEnabled(False)
        self.load_graph_from_file.clicked.connect(self.prepare_graph_and_network)
        self.from_but.clicked.connect(self.search_for_point_from)
        self.to_but.clicked.connect(self.search_for_point_to)
        self.do_dist_matrix.clicked.connect(self.produces_path)

    def prepare_graph_and_network(self):
        dlg2 = LoadGraphLayerSettingDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.error is None:
            self.link_features = dlg2.link_features
            self.line_layer = dlg2.line_layer
            self.node_layer = dlg2.node_layer
            self.node_keys = dlg2.node_keys
            self.node_id = dlg2.node_id
            self.node_fields = dlg2.node_fields
            self.index = dlg2.index
            self.graph = dlg2.graph
            self.res.prepare(self.graph)
            self.do_dist_matrix.setEnabled(True)

    def clear_memory_layer(self):
        self.link_features = None

    def search_for_point_from(self):
        self.iface.mapCanvas().setMapTool(self.clickTool)
        QObject.connect(self.clickTool, SIGNAL("clicked"), self.fill_path_from)
        self.from_but.setEnabled(False)

    def search_for_point_to(self):
        self.iface.mapCanvas().setMapTool(self.clickTool)
        QObject.connect(self.clickTool, SIGNAL("clicked"), self.fill_path_to)
        self.to_but.setEnabled(False)

    def fill_path_to(self):
        self.toNode = self.find_point()
        self.path_to.setText(str(self.toNode))
        self.to_but.setEnabled(True)

    def fill_path_from(self):
        self.fromNode = self.find_point()
        self.path_from.setText(str(self.fromNode))
        self.from_but.setEnabled(True)
        self.search_for_point_to()

    def find_point(self):
        try:
            point = self.clickTool.point
            nearest = self.index.nearestNeighbor(point, 1)
            self.iface.mapCanvas().setMapTool(None)
            self.clickTool = PointTool(self.iface.mapCanvas())
            node_id = self.node_keys[nearest[0]]

            index_field = self.node_fields.index(self.node_id)
            node_actual_id = node_id[index_field]
            return node_actual_id
        except:
            pass

    def produces_path(self):
        self.to_but.setEnabled(True)
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
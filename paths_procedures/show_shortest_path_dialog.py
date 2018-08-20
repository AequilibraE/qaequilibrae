"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Shortest path computation
 Purpose:    Dialog for computing and displaying shortest paths based on clicks on the map

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
import qgis
from qgis.core import *
from qgis.gui import QgsMapToolEmitPoint
from qgis.utils import iface
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt import QtCore
from qgis.PyQt import QtWidgets, uic
from random import randint

import sys
import os
from ..common_tools.auxiliary_functions import *
from .point_tool import PointTool
from aequilibrae.paths.results import PathResults

no_binary = False
try:
    from aequilibrae.paths import path_computation
except:
    no_binary = True

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/")

# sys.modules['qgsmaplayercombobox'] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_compute_path.ui'))

from ..common_tools import LoadGraphLayerSettingDialog


class ShortestPathDialog(QtWidgets.QDialog, FORM_CLASS):
    clickTool = PointTool(iface.mapCanvas())
    def __init__(self, iface):
        # QtWidgets.QDialog.__init__(self)
        QtWidgets.QDialog.__init__(self, None, Qt.WindowStaysOnTopHint)
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
        if dlg2.error is None and dlg2.graph_ok:
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
        self.clickTool.clicked.connect(self.fill_path_from)
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.from_but.setEnabled(False)

    def search_for_point_to(self):
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.clickTool.clicked.connect(self.fill_path_to)
        self.to_but.setEnabled(False)

    def search_for_point_to_after_from(self):
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.clickTool.clicked.connect(self.fill_path_to)

    def fill_path_to(self):
        self.to_node = self.find_point()
        self.path_to.setText(str(self.to_node))
        self.to_but.setEnabled(True)

    @QtCore.pyqtSlot()
    def fill_path_from(self):
        self.from_node = self.find_point()
        self.path_from.setText(str(self.from_node))
        self.from_but.setEnabled(True)
        self.search_for_point_to_after_from()

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
        if self.path_from.text().isdigit() and self.path_to.text().isdigit():
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
                vl = QgsVectorLayer("LineString?crs={}".format(crs), self.path_from.text() +
                                    " to " + self.path_to.text(), "memory")
                pr = vl.dataProvider()

                # add fields
                pr.addAttributes(self.line_layer.dataProvider().fields())
                vl.updateFields()  # tell the vector layer to fetch changes from the provider

                # add a feature
                all_links = []
                for k in self.res.path:
                    fet = self.link_features[k]
                    all_links.append(fet)

                # add all links to the temp layer
                pr.addFeatures(all_links)

                # add layer to the map
                QgsProject.instance().addMapLayer(vl)

                symbol = vl.renderer().symbol()
                symbol.setWidth(1)
                qgis.utils.iface.mapCanvas().refresh()

            else:
                qgis.utils.iface.messageBar().pushMessage("No path between " + self.path_from.text() +
                                                          ' and ' + self.path_to.text(), '', level=3)

    def exit_procedure(self):
        self.close()

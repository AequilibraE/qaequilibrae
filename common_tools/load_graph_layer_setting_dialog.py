"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loads graph from file
 Purpose:    Loads GUI for loading graphs from files and configuring them before computation

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

from qgis.core import *
import qgis
from qgis.PyQt import QtWidgets, uic, QtCore, QtGui
from qgis.PyQt.QtGui import *

import sys
import os
from functools import partial
from ..common_tools.auxiliary_functions import *
from ..common_tools import GetOutputFileName
from ..common_tools.global_parameters import *

try:
    from aequilibrae.paths import Graph

    no_binary = False
except:
    no_binary = True

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_load_network_info.ui"))


class LoadGraphLayerSettingDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        # QtWidgets.QDialog.__init__(self)
        QtWidgets.QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        self.iface = iface
        self.setupUi(self)
        self.field_types = {}
        self.node_layer = None
        self.line_layer = None
        self.index = None
        self.graph = Graph()
        self.skimmeable_fields = None
        self.link_features = None
        self.link_layer = None
        self.link_id = None
        self.node_layer = None
        self.node_id = None
        self.node_fields = None
        self.node_keys = None
        self.error = None
        self.graph_ok = False

        self.load_graph_from_file.clicked.connect(self.loaded_new_graph_from_file)

        self.cb_node_layer.currentIndexChanged.connect(
            partial(self.load_fields_to_combo_boxes, self.cb_node_layer, self.cb_data_field, True)
        )

        self.cb_link_layer.currentIndexChanged.connect(
            partial(self.load_fields_to_combo_boxes, self.cb_link_layer, self.cb_link_id_field, False)
        )

        self.cb_link_id_field.currentIndexChanged.connect(self.clear_memory_layer)

        self.do_load_graph.clicked.connect(self.returns_configuration)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if "wkbType" in dir(layer):
                if layer.wkbType() in point_types:
                    self.cb_node_layer.addItem(layer.name())

                if layer.wkbType() in line_types:
                    self.cb_link_layer.addItem(layer.name())

        # loads default path from parameters
        self.path = standard_path()

    def check_parameters(self):
        if self.cb_node_layer.currentIndex() >= 0 and self.cb_data_field.currentIndex() >= 0:
            return True
        else:
            qgis.utils.iface.messageBar().pushMessage(
                "Wrong settings", "Please select node layer and ID field", level=3, duration=3
            )
            return False

    def clear_memory_layer(self):
        self.link_features = None

    def load_fields_to_combo_boxes(self, combobox, combofield, node_layer):
        combofield.clear()
        if combobox.currentIndex() >= 0:
            layer = get_vector_layer_by_name(combobox.currentText())
            for field in layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    combofield.addItem(field.name())
            if node_layer:
                # We create the spatial index used to associate the click to the network nodes
                self.node_fields = [field.name() for field in layer.dataProvider().fields().toList()]
                self.node_keys = {}
                self.index = QgsSpatialIndex()
                self.node_layer = layer
                for feature in layer.getFeatures():
                    self.index.insertFeature(feature)
                    self.node_keys[feature.id()] = feature.attributes()

            else:
                self.line_layer = layer

    def loaded_new_graph_from_file(self):
        file_types = "AequilibraE graph(*.aeg)"
        new_name, type = GetOutputFileName(self, "Result file", [file_types], ".aeg", self.path)

        self.cb_minimizing.clear()
        self.block_paths.setChecked(False)
        try:
            self.graph_file_name.setText(new_name)
            self.graph.load_from_disk(new_name)

            if self.graph.block_centroid_flows:
                self.block_paths.setChecked(True)
            graph_fields = list(self.graph.graph.dtype.names)
            self.skimmeable_fields = [
                x for x in graph_fields if x not in ["link_id", "a_node", "b_node", "direction", "id"]
            ]

            for q in self.skimmeable_fields:
                self.cb_minimizing.addItem(q)
            self.graph_ok = True
        except:
            pass

    def returns_configuration(self):
        if self.link_features is None:
            idx = self.line_layer.dataProvider().fieldNameIndex(self.cb_link_id_field.currentText())
            self.link_features = {}
            for feat in self.line_layer.getFeatures():
                link_id = feat.attributes()[idx]
                self.link_features[link_id] = feat
        self.node_id = self.cb_data_field.currentText()
        self.cb_link_id_field = self.cb_link_id_field.currentText()
        self.exit_procedure()

    def exit_procedure(self):
        if None in [self.line_layer, self.node_layer, self.node_keys, self.node_fields]:
            self.error = "Layers and fields not chosen correctly"
        if not self.graph_ok:
            self.error = "Graph not loaded"
        self.close()

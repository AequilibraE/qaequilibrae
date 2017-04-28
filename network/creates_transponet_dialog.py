"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Main interface for creating a TranspoNet from layers previously prepared
 Purpose:    Load GUI and user interface for TranspoNet creation

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE
 Transponet Repository: https://github.com/AequilibraE/TranspoNet

 Created:    2017-04-28
 Updated:    
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from auxiliary_functions import *
import sys
from qgis.gui import QgsMapLayerProxyModel
import os
from global_parameters import *
from functools import partial

sys.modules['qgsmaplayercombobox'] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                            'forms/ui_transponet_construction.ui'))

class CreatesTranspoNetDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.path = standard_path()

        self.required_fields_links = ['link_id', 'a_node', 'b_node', 'direction', 'length', 'capacity_ab',
                                      'capacity_ba', 'speed_ab', 'speed_ba']

        self.required_fields_nodes = ['node_id']

        self.link_layer = False
        self.node_layer = False
        self.but_create_network_file.clicked.connect(self.create_net)

        self.node_layers_list.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.node_layers_list.layerChanged.connect(partial (self.changed_layer, 'nodes'))

        self.link_layers_list.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.link_layers_list.layerChanged.connect(partial (self.changed_layer, 'links'))

    def changed_layer(self, layer):
        if layer == 'nodes':
            table = self.table_node_fields
            self.node_layer = get_vector_layer_by_name(self.node_layers_list.currentText())
            layer = self.node_layer
        else:
            table = self.table_link_fields
            self.link_layer = get_vector_layer_by_name(self.link_layers_list.currentText())
            layer = self.link_layer

        # We create the comboboxes that will hold the definitions for all the fields that are mandatory for
        # creating the appropriate triggers on the SQLite file
        fields = [field.name() for field in layer.pendingFields()]
        required_fields_links = QComboBox()
        for i in self.required_fields_links:
            required_fields_links.addItem(i)

        required_fields_nodes = QComboBox()
        for i in self.required_fields_nodes:
            required_fields_nodes.addItem(i)

        chbox = QCheckBox()

        counter = 0
        for field in fields:
            table.setRowCount(counter + 1)

            table.setItem(counter, 0, QTableWidgetItem(field))

            counter =+ 1

            #
            # # color
            # if self.ramps is None:
            #     self.bands_list.setItem(self.tot_bands, 2, QTableWidgetItem(''))
            #     self.bands_list.item(self.tot_bands, 2).setBackground(self.mColorButton.color())
            # else:
            #     self.bands_list.setItem(self.tot_bands, 2, QTableWidgetItem(str(self.ramps)))
            #     self.ramps = None
            #     self.rdo_color.setChecked(True)
            #
            # # Up-Down buttons
            #
            # button_up = QToolButton()
            # button_up.setArrowType(Qt.UpArrow)
            # button_up.clicked.connect(self.click_button_inside_the_list)
            #
            #
            # self.node_fields.clear()
            # if self.nodelayers.currentIndex() >= 0:
            #     layer = get_vector_layer_by_name(self.nodelayers.currentText())
            #     for field in layer.dataProvider().fields().toList():
            #         self.node_fields.addItem(field.name())


    def create_net(self):
        pass
        # DONE


    def exit_procedure(self):
        self.close()
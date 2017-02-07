"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       TranspoNet preparation dialog
 Purpose:    creates a consistent network file from a set of links and nodes
             Please refer to https://github.com/AequilibraE/TranspoNet

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-01-20
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from qgis.gui import QgsMapLayerProxyModel
from functools import partial

import sys
from global_parameters import *
from auxiliary_functions import *

#from Network_preparation_procedure import FindsNodes
#from ui_TQ_NetPrep import *


class TranspoNetPreparationDialog(QDialog, Ui_transponet_construction):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.path = standard_path()

        self.required_fields_links = ['link_id', 'node_a', 'node_b', 'direction', 'length']
        self.required_fields_nodes = ['node_id']

        self.link_layer = False
        self.node_layer = False
        self.but_create_network_file.clicked.connect(self.uses_nodes)

        self.node_layers_list.setFilters(QgsMapLayerProxyModel.NodeLayer)
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


    def run(self):
        pass
        # DONE


    def exit_procedure(self):
        self.close()


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
 Updated:    2020-02-08
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
from aequilibrae.project import Project

try:
    from aequilibrae.paths import Graph

    no_binary = False
except:
    no_binary = True

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_load_network_info.ui"))


class LoadGraphLayerSettingDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, project: Project):
        # QtWidgets.QDialog.__init__(self)
        QtWidgets.QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        self.iface = iface
        self.project = project
        self.setupUi(self)
        self.minimize_field = ''
        self.mode = ''
        self.link_layer = ''
        self.node_layer = ''
        self.error = []
        self.all_modes = {}

        curr = self.project.network.conn.cursor()
        curr.execute("""select mode_name, mode_id from modes""")

        for x in curr.fetchall():
            self.cb_modes.addItem(f'{x[0]} ({x[1]})')
            self.all_modes[f'{x[0]} ({x[1]})'] = x[1]

        for field in self.project.network.skimmable_fields():
            self.cb_minimizing.addItem(field)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if "wkbType" in dir(layer):
                if layer.wkbType() in point_types:
                    self.cb_node_layer.addItem(layer.name())

                if layer.wkbType() in line_types:
                    self.cb_link_layer.addItem(layer.name())

        # loads default path from parameters
        self.path = standard_path()
        self.do_load_graph.clicked.connect(self.exit_procedure)

    def exit_procedure(self):
        self.mode = self.all_modes[self.cb_modes.currentText()]
        self.link_layer = self.cb_link_layer.currentText()
        self.node_layer = self.cb_node_layer.currentText()
        self.minimize_field = self.cb_minimizing.currentText()
        self.block_connector = self.block_paths.isChecked()
        self.close()

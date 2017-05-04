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

from qgis.core import *
from PyQt4 import QtGui, QtCore, uic
from ..common_tools.auxiliary_functions import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/advanced_graph_details.ui'))

class GraphAdvancedFeatures(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface):
        #QtGui.QDialog.__init__(self)
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        self.iface = iface
        self.setupUi(self)
        self.field_types = {}
        self.selected_only = False
        self.block_through_centroids = False
        self.centroids = None

        self.but_ok.clicked.connect(self.exit_procedure)
        self.set_centroids_rule.stateChanged.connect(self.check_centroids_option)

    def check_centroids_option(self):
        if self.set_centroids_rule.isChecked():
            self.model_centroids.setEnabled(True)
        else:
            self.model_centroids.setEnabled(False)
            self.centroids = None

    def exit_procedure(self):
        if self.use_link_selection.isChecked():
            self.selected_only = True

        if self.path_through_centroids.isChecked():
            self.block_through_centroids = True

        if self.set_centroids_rule.isChecked():
            self.centroids = self.model_centroids.text()
            if not isinstance(self.centroids, int):
                self.centroids = None

        self.close()
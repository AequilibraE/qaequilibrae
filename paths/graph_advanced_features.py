"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Setting graph options
 Purpose:    Dialog for inputing number of centroids, blocking flows through path and to use only selected links

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    01/01/2017
 Updated:    31/05/2017
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
        self.model_centroids.setEnabled(self.set_centroids_rule.isChecked())
        if not self.set_centroids_rule.isChecked():
            self.centroids = None

    def exit_procedure(self):
        if self.use_link_selection.isChecked():
            self.selected_only = True

        if self.path_through_centroids.isChecked():
            self.block_through_centroids = True

        if self.set_centroids_rule.isChecked():
            self.centroids = self.model_centroids.text()

            if self.centroids.isdigit():
                self.centroids = int(self.centroids)
            else:
                self.centroids = None

        self.close()
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
 Updated:    31/11/2017
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import sys
from qgis.gui import QgsMapLayerProxyModel  # , QgsFieldProxyModel
from PyQt4 import QtGui, QtCore, uic
from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import integer_types
import numpy as np

sys.modules['qgsmaplayercombobox'] = qgis.gui
# sys.modules['qgsfieldcombobox'] = qgis.gui
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
        self.error = None
        self.layer = None
        self.num_zones = -1

        self.chb_set_centroids.stateChanged.connect(self.check_centroids_option)
        self.cob_centroids_layer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.cob_centroids_layer.layerChanged.connect(self.changed_layer)
        self.but_ok.clicked.connect(self.exit_procedure)

    def check_centroids_option(self):
        self.frm_all_items.setEnabled(self.chb_set_centroids.isChecked())
        if not self.chb_set_centroids.isChecked():
            self.centroids = None
            self.but_ok.setText('Cancel')
        else:
            self.but_ok.setText('Ok')
            self.changed_layer()

    def changed_layer(self):
        self.cob_centroid_id.clear()
        if self.cob_centroids_layer.currentIndex() > 0:
            for field in self.cob_centroids_layer.currentLayer().pendingFields().toList():
                if field.type() in integer_types:
                    self.cob_centroid_id.addItem(field.name())

    def exit_procedure(self):
        if self.chb_set_centroids.isChecked() and self.cob_centroid_id.currentIndex() > 0:
            self.block_through_centroids = self.path_through_centroids.isChecked()

            if self.use_link_selection.isChecked():
                features = self.layer.selectedFeatures()
            else:
                features = self.layer.getFeatures()

            idx = self.layer.fieldNameIndex(self.cob_centroid_id.currentText())
            self.centroids = []
            for feat in features:
                self.centroids.append(feat.attributes()[idx])
            self.centroids = np.array(self.centroids)
            if self.centroids.min() <= 0:
                self.error = 'Centroid IDs need to be positive'
            else:
                if np.bincount(self.centroids).max() > 1:
                    self.error = 'Centroids field is not unique'
            self.num_zones = self.centroids.shape[0]

        else:
            self.centroids = None
            self.num_zones = -1
        self.close()
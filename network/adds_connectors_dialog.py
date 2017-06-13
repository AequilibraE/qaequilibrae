"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Main interface for adding centroid connectors
 Purpose:    Load GUI and user interface for the centroid addition procedure

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    21/12/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from qgis.gui import QgsMapLayerProxyModel
from functools import partial

from ..common_tools.auxiliary_functions import *
import sys
import os
from ..common_tools.global_parameters import *

from adds_connectors_procedure import AddsConnectorsProcedure

sys.modules['qgsfieldcombobox'] = qgis.gui
sys.modules['qgsmaplayercombobox'] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_connecting_centroids.ui'))

class AddConnectorsDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.NewLinks = False
        self.NewNodes = False

        self.IfMaxLength.toggled.connect(self.allows_distance)
        self.pushOK.clicked.connect(self.run)
        self.pushClose.clicked.connect(self.exit_procedure)

        self.NodeLayer.layerChanged.connect(partial(self.set_fields,'nodes'))
        self.CentroidLayer.layerChanged.connect(partial(self.set_fields,'centroids'))

        for i in xrange(1, 21):
            self.NumberConnectors.addItem(str(i))

        # We load the line and node layers existing in our canvas
        self.LineLayer.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.NodeLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.CentroidLayer.setFilters(QgsMapLayerProxyModel.PointLayer)

        # default directory
        self.path = standard_path()
        self.set_fields('nodes')
        self.set_fields('centroids')

    def allows_distance(self):
        self.MaxLength.setEnabled(False)
        if self.IfMaxLength.isChecked():
            self.MaxLength.setEnabled(True)

    def run_thread(self):
        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"),
                        self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("jobFinished( PyQt_PyObject )"), self.job_finished_from_thread)
        self.worker_thread.start()
        self.show()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value)

    def set_fields(self, lyr):
        if lyr in ['nodes', 'centroids']:
            if lyr == "nodes":
                self.NodeField.setLayer(self.NodeLayer.currentLayer())

            if lyr == "centroids":
                self.CentroidField.setLayer(self.CentroidLayer.currentLayer())

    def job_finished_from_thread(self, success):
        self.pushOK.setEnabled(True)
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Node layer error: ", self.worker_thread.error, level=3)
        else:
            QgsMapLayerRegistry.instance().addMapLayer(self.worker_thread.new_node_layer)
            QgsMapLayerRegistry.instance().addMapLayer(self.worker_thread.new_line_layer)
        self.exit_procedure()

    def run(self):

        max_length = None
        if self.MaxLength.isEnabled():
            max_length = float(self.MaxLength.text())
        selection_only = False
        if self.SelectedNodes.isChecked():
            selection_only = True

        parameters = [self.NodeLayer.currentText(),
                      self.LineLayer.currentText(),
                      self.CentroidLayer.currentText(),
                      self.NodeField.currentText(),
                      self.CentroidField.currentText(),
                      max_length,
                      int(self.NumberConnectors.currentText()),
                      self.OutLinks.text(),
                      self.OutNodes.text(),
                      selection_only]

        #  WE NEED TO ADD SOME ERROR TREATMENT CODE HERE

        self.pushOK.setEnabled(False)
        self.worker_thread = AddsConnectorsProcedure(qgis.utils.iface.mainWindow(), *parameters)
        self.run_thread()

    def exit_procedure(self):
        self.close()

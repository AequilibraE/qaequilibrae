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
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from auxiliary_functions import *
import sys
import os
from global_parameters import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/algorithms/")

from adds_connectors_procedure import AddsConnectorsProcedure
from ui_ConnectingCentroids import Ui_ConnectingCentroids


class AddConnectorsDialog(QDialog, Ui_ConnectingCentroids):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.NewLinks = False
        self.NewNodes = False

        self.IfMaxLength.toggled.connect(self.allows_distance)
        self.pushOK.clicked.connect(self.run)
        self.pushClose.clicked.connect(self.exit_procedure)

        self.ChooseLineLayer.clicked.connect(self.browse_line_layer)
        self.ChooseNodeLayer.clicked.connect(self.browse_node_layer)

        QObject.connect(self.CentroidLayer, SIGNAL("currentIndexChanged(QString)"), self.set_field_centroids)
        QObject.connect(self.NodeLayer, SIGNAL("currentIndexChanged(QString)"), self.set_field_nodes)

        for i in xrange(1, 21):
            self.NumberConnectors.addItem(str(i))

        # We load the line and node layers existing in our canvas
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if layer.wkbType() in line_types:
                self.LineLayer.addItem(layer.name())

            if layer.wkbType() in point_types:
                self.NodeLayer.addItem(layer.name())
                self.CentroidLayer.addItem(layer.name())

        # default directory
        self.path = standard_path()

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

    def set_field_centroids(self):
        self.CentroidField.clear()
        if self.CentroidLayer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.CentroidLayer.currentText())
            for field in layer.dataProvider().fields().toList():
                self.CentroidField.addItem(field.name())

    def set_field_nodes(self):
        self.NodeField.clear()
        if self.NodeLayer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.NodeLayer.currentText())
            for field in layer.dataProvider().fields().toList():
                self.NodeField.addItem(field.name())

    def browse_node_layer(self):
        if len(self.OutNodes.text()) == 0:
            new_name = QFileDialog.getSaveFileName(None, 'Result file', self.path, "Shapefile(*.shp)")
        else:
            new_name = QFileDialog.getSaveFileName(None, 'Result file', self.OutNodes.text(), "Shapefile(*.shp)")
        self.OutNodes.setText(new_name)
        self.NewNodes = True
        if len(new_name) == 0:
            self.NewNodes = False

    def browse_line_layer(self):
        if len(self.OutLinks.text()) == 0:
            new_name = QFileDialog.getSaveFileName(None, 'Result file', self.path, "Shapefile(*.shp)")
        else:
            new_name = QFileDialog.getSaveFileName(None, 'Result file', self.OutLinks.text(), "Shapefile(*.shp)")
        self.OutLinks.setText(new_name)
        self.NewLinks = True
        if len(new_name) == 0:
            self.NewLinks = False

    def job_finished_from_thread(self, success):
        self.pushOK.setEnabled(True)
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Node layer error: ", self.worker_thread.error, level=3)

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

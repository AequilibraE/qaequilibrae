"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Network preparation
 Purpose:    Loads GUI for preparing networks (extracting nodes A and B from links)

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import sys
from global_parameters import *
from auxiliary_functions import *


sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "//forms//")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "//algorithms//")


from Network_preparation_procedure import FindsNodes
from ui_TQ_NetPrep import *
class TQ_NetPrepDialog(QDialog, Ui_TQ_NetPrep):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.filename = False
        self.new_layer = False
        self.radioUseNodes.clicked.connect(self.uses_nodes)
        self.radioNewNodes.clicked.connect(self.uses_nodes)

        QObject.connect(self.nodelayers, SIGNAL("currentIndexChanged(QString)"), self.set_columns_nodes)
        self.pushOK.clicked.connect(self.run)
        self.pushClose.clicked.connect(self.exit_procedure)

        self.select_new_line_layer.clicked.connect(self.set_new_line_layer)

        # We load the line and node layers existing in our canvas
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if 'wkbType' in dir(layer):
                if layer.wkbType() in line_types:
                    self.linelayers.addItem(layer.name())
                # if layer.wkbType() == QGis.WKBPoint: self.nodelayers.addItem(layer.name())

        # loads default path from parameters
        self.path = standard_path()

    def run_thread(self):
        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("jobFinished( PyQt_PyObject )"), self.job_finished_from_thread)
        self.worker_thread.start()
        self.show()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value)

    def set_columns_nodes(self):
        self.node_fields.clear()
        if self.nodelayers.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.nodelayers.currentText())
            for field in layer.dataProvider().fields().toList():
                self.node_fields.addItem(field.name())

    def set_new_line_layer(self):
        if not len(self.out_lines.text()):
            new_name = QFileDialog.getSaveFileName(None, 'Result file', self.path, "Shapefile(*.shp)")
        else:
            new_name = QFileDialog.getSaveFileName(None, 'Result file', self.out_lines.text(), "Shapefile(*.shp)")
        self.out_lines.setText(new_name)
        self.new_layer = True
        if not len(new_name):
            self.new_layer = False

    def uses_nodes(self, state):
        if (self.radioUseNodes.isChecked()):
            self.nodelayers.clear()
            self.node_fields.clear()
            self.np_node_start.setEnabled(False)
            for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
                if layer.wkbType() in point_types:
                    self.nodelayers.addItem(layer.name())
        else:
            self.nodelayers.clear()
            self.node_fields.clear()
            self.nodelayers.hideEvent
            self.np_node_start.setEnabled(True)
            if len(self.out_nodes.text()) == 0:
                new_name = QFileDialog.getSaveFileName(None, 'Result file', self.path, "Shapefile(*.shp)")
            else:
                new_name = QFileDialog.getSaveFileName(None, 'Result file', self.out_nodes.text(), "Shapefile(*.shp)")
            if len(new_name) > 0:
                self.out_nodes.setText(new_name)
                self.filename = True

    def job_finished_from_thread(self, success):
        self.pushOK.setEnabled(True)
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Node layer error: ", self.worker_thread.error, level=3)
        print 'Finished OK'

    def run(self):
        if self.new_layer:

            if self.radioUseNodes.isChecked():
                self.pushOK.setEnabled(False)
                self.worker_thread = FindsNodes(qgis.utils.iface.mainWindow(), self.linelayers.currentText(),
                                               self.out_lines.text(), self.nodelayers.currentText(),
                                               self.node_fields.currentText())
                self.run_thread()

            else:
                if self.filename:
                    self.pushOK.setEnabled(False)
                    self.worker_thread = FindsNodes(qgis.utils.iface.mainWindow(), self.linelayers.currentText(),
                                                   self.out_lines.text(), new_node_layer=self.out_nodes.text(),
                                                    node_start = int(self.np_node_start.text()))
                    self.run_thread()

                else:
                    qgis.utils.iface.messageBar().pushMessage("No file name provided",
                                                              "Please indicate a file name for the new NODE layer",
                                                              level=3)
        else:
            qgis.utils.iface.messageBar().pushMessage("No file name provided",
                                                      "Please indicate a file name for the new LINE layer", level=3)

    def exit_procedure(self):
        self.close()


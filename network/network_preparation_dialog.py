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
 Updated:    21/12/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import uic

import sys
from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import *

from Network_preparation_procedure import FindsNodes

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_network_preparation.ui'))

class NetworkPreparationDialog(QDialog, FORM_CLASS):
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

        # We load the line and node layers existing in our canvas
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if 'wkbType' in dir(layer):
                if layer.wkbType() in line_types:
                    self.linelayers.addItem(layer.name())

        # loads default path from parameters
        self.path = standard_path()
        self.uses_nodes()

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

    def uses_nodes(self):
        q = [self.OutNodes, self.label_9, self.np_node_start, self.label_3]
        w = [self.nodelayers, self.node_fields, self.label_2, self.label_4]

        if self.radioUseNodes.isChecked():
            for i in q:
                i.setVisible(False)
            for i in w:
                i.setVisible(True)

            self.nodelayers.clear()
            self.node_fields.clear()
            self.np_node_start.setEnabled(False)
            for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
                if layer.wkbType() in point_types:
                    self.nodelayers.addItem(layer.name())
        else:
            for i in q:
                i.setVisible(True)
            for i in w:
                i.setVisible(False)

            self.nodelayers.clear()
            self.node_fields.clear()
            self.nodelayers.hideEvent
            self.np_node_start.setEnabled(True)

    def job_finished_from_thread(self, success):
        self.pushOK.setEnabled(True)
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Node layer error: ", self.worker_thread.error, level=3)
        else:
            QgsMapLayerRegistry.instance().addMapLayer(self.worker_thread.new_line_layer)
            if self.worker_thread.new_node_layer:
                QgsMapLayerRegistry.instance().addMapLayer(self.worker_thread.new_node_layer)


    def run(self):
        if self.radioUseNodes.isChecked():
            self.pushOK.setEnabled(False)
            self.worker_thread = FindsNodes(qgis.utils.iface.mainWindow(), self.linelayers.currentText(),
                                           self.OutLinks.text(), self.nodelayers.currentText(),
                                           self.node_fields.currentText())
            self.run_thread()

        else:
            self.pushOK.setEnabled(False)
            self.worker_thread = FindsNodes(qgis.utils.iface.mainWindow(), self.linelayers.currentText(),
                                           self.OutLinks.text(), new_node_layer=self.OutNodes.text(),
                                            node_start = int(self.np_node_start.text()))
            self.run_thread()


    def exit_procedure(self):
        self.close()


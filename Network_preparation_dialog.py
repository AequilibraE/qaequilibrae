"""
/***************************************************************************
 AequilibraE - www.AequilibraE.com
 
    Name:        Dialogs for modeling tools
                              -------------------
        begin                : 2014-03-19
        copyright            : TOOLS developers 2014
        Original Author: Pedro Camargo pedro@xl-optim.com
        Contributors: 
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""
from qgis.core import *
import qgis
from PyQt4 import QtGui
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import sys
# from NumpyModel import NumpyModel
from global_parameters import *
from auxiliary_functions import *


sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\\forms\\")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\\algorithms\\")


from Network_preparation_procedure import FindsNodes
from ui_TQ_NetPrep import *
class TQ_NetPrepDialog(QDialog, Ui_TQ_NetPrep):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.filename = False
        self.new_layer = False
        QObject.connect(self.radioUseNodes, QtCore.SIGNAL("clicked(bool)"), self.uses_nodes)
        QObject.connect(self.radioNewNodes, QtCore.SIGNAL("clicked(bool)"), self.uses_nodes)

        QObject.connect(self.nodelayers, SIGNAL("currentIndexChanged(QString)"), self.set_columns_nodes)
        self.pushOK.clicked.connect(self.run)
        self.pushClose.clicked.connect(self.ExitProcedure)

        self.select_new_line_layer.clicked.connect(self.set_new_line_layer)

        # We load the line and node layers existing in our canvas
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if layer.wkbType() in line_types:
                self.linelayers.addItem(layer.name())
            # if layer.wkbType() == QGis.WKBPoint: self.nodelayers.addItem(layer.name())

        # loads default path from parameters
        self.path = standard_path()


    def runThread(self):
        QObject.connect(self.workerThread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.ProgressValueFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressText( PyQt_PyObject )"), self.ProgressTextFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.ProgressRangeFromThread)
        QObject.connect(self.workerThread, SIGNAL("jobFinished( PyQt_PyObject )"), self.jobFinishedFromThread)
        self.workerThread.start()
        self.show()

    def ProgressRangeFromThread(self, val):
        self.progressbar.setRange(0, val)

    def ProgressValueFromThread(self, value):
        self.progressbar.setValue(value)

    def ProgressTextFromThread(self, value):
        self.progress_label.setText(value)

    def browse_outfile(self):
        if len(self.outdirname.displayText()) == 0:
            newname = QFileDialog.getExistingDirectory(None, "Output Frames Directory", self.path)
        else:
            newname = QFileDialog.getExistingDirectory(None, "Output Frames Directory", self.outdirname.displayText())

    def set_columns_nodes(self):
        self.node_fields.clear()
        if self.nodelayers.currentIndex() >= 0:
            layer = getVectorLayerByName(self.nodelayers.currentText())
            for field in layer.dataProvider().fields().toList():
                self.node_fields.addItem(field.name())

    def set_new_line_layer(self):
        if len(self.out_lines.text()) == 0:
            newname = QFileDialog.getSaveFileName(None, 'Result file', self.path, "Shapefile(*.shp)")
        else:
            newname = QFileDialog.getSaveFileName(None, 'Result file', self.out_lines.text(), "Shapefile(*.shp)")
        self.out_lines.setText(newname)
        self.new_layer = True
        if len(newname) == 0: self.new_layer = False

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
                newname = QFileDialog.getSaveFileName(None, 'Result file', self.path, "Shapefile(*.shp)")
            else:
                newname = QFileDialog.getSaveFileName(None, 'Result file', self.out_nodes.text(), "Shapefile(*.shp)")
            if len(newname) > 0:
                self.out_nodes.setText(newname)
                self.filename = True

    def jobFinishedFromThread(self, success):
        self.pushOK.setEnabled(True)
        if self.workerThread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Node layer error: ", self.workerThread.error, level=3)
        print 'Finished OK'
    def run(self):

        if self.new_layer:

            if self.radioUseNodes.isChecked():
                self.pushOK.setEnabled(False)
                self.workerThread = FindsNodes(qgis.utils.iface.mainWindow(), self.linelayers.currentText(),
                                               self.out_lines.text(), self.nodelayers.currentText(),
                                               self.node_fields.currentText())
                self.runThread()

            else:
                if self.filename == True:
                    self.pushOK.setEnabled(False)
                    self.workerThread = FindsNodes(qgis.utils.iface.mainWindow(), self.linelayers.currentText(),
                                                   self.out_lines.text(), new_node_layer=self.out_nodes.text(), node_start = int(self.np_node_start.text()))
                    self.runThread()

                else:
                    qgis.utils.iface.messageBar().pushMessage("No file name provided",
                                                              "Please indicate a file name for the new NODE layer",
                                                              level=3)
        else:
            qgis.utils.iface.messageBar().pushMessage("No file name provided",
                                                      "Please indicate a file name for the new LINE layer", level=3)

    def ExitProcedure(self):
        self.close()


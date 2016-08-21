"""
/***************************************************************************
 AequilibraE - www.aequilibrae.com

    Name:        Main interface for adding centroid connectors
                              -------------------
        Creation           2014-03-19
        Update             2016-07-30
        copyright          AequilibraE developers 2014
        Original Author    Pedro Camargo pedro@xl-optim.com
        Contributors:
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""

import qgis
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from auxiliary_functions import *
from global_parameters import *
import sys, os
from global_parameters import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\\forms\\")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\\algorithms\\")

from adds_connectors_procedure import AddsConnectorsProcedure
from ui_ConnectingCentroids import *
class AEQ_AddConnectors(QDialog,Ui_ConnectingCentroids):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.NewLinks = False
        self.NewNodes = False

        self.IfMaxLength.toggled.connect(self.allows_distance)
        self.pushOK.clicked.connect(self.run)
        self.pushClose.clicked.connect(self.ExitProcedure)

        self.ChooseLineLayer.clicked.connect(self.BrowseLineLayer)
        self.ChooseNodeLayer.clicked.connect(self.BrowseNodeLayer)

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

    def set_field_centroids(self):
        self.CentroidField.clear()
        if self.CentroidLayer.currentIndex() >= 0:
            layer = getVectorLayerByName(self.CentroidLayer.currentText())
            for field in layer.dataProvider().fields().toList():
                self.CentroidField.addItem(field.name())

    def set_field_nodes(self):
        self.NodeField.clear()
        if self.NodeLayer.currentIndex() >= 0:
            layer = getVectorLayerByName(self.NodeLayer.currentText())
            for field in layer.dataProvider().fields().toList():
                self.NodeField.addItem(field.name())

    def BrowseNodeLayer(self):
        if len(self.OutNodes.text()) == 0:
            newname = QFileDialog.getSaveFileName(None, 'Result file', self.path, "Shapefile(*.shp)")
        else:
            newname = QFileDialog.getSaveFileName(None, 'Result file', self.OutNodes.text(), "Shapefile(*.shp)")
        self.OutNodes.setText(newname)
        self.NewNodes = True
        if len(newname) == 0:
            self.NewNodes = False

    def BrowseLineLayer(self):
        if len(self.OutLinks.text()) == 0:
            newname = QFileDialog.getSaveFileName(None, 'Result file', self.path, "Shapefile(*.shp)")
        else:
            newname = QFileDialog.getSaveFileName(None, 'Result file', self.OutLinks.text(), "Shapefile(*.shp)")
        self.OutLinks.setText(newname)
        self.NewLinks = True
        if len(newname) == 0:
            self.NewLinks = False

    def jobFinishedFromThread(self, success):
        self.pushOK.setEnabled(True)
        if self.workerThread.error != None:
            qgis.utils.iface.messageBar().pushMessage("Node layer error: ", self.workerThread.error, level=3)

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
        self.workerThread = AddsConnectorsProcedure(qgis.utils.iface.mainWindow(), *parameters)
        self.runThread()

    def ExitProcedure(self):
        self.close()
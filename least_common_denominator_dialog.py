"""
/***************************************************************************
 AequilibraE - www.aequilibrae.com
 
    Name:        Dialogs for GIS tools
                              -------------------
        begin                : 2014-03-19
        copyright            : AequilibraE developers 2014
        Original Author: Pedro Camargo pedro@xl-optim.com
        Contributors: 
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""

from qgis.core import QgsMapLayerRegistry
from PyQt4.QtCore import QObject, SIGNAL
import qgis
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")

# For the GIS tools portion
from least_common_denominator_procedure import LeastCommonDenominator
from ui_least_common_denominator import *
from global_parameters import *
from functools import partial
from auxiliary_functions import getVectorLayerByName
from least_common_denominator_procedure import LeastCommonDenominator
#####################################################################################################
###################################        SIMPLE TAG          ######################################

class LeastCommonDenominatorDialog(QtGui.QDialog, Ui_least_common_denominator):
    def __init__(self, iface):
        QtGui.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        # The whole software is prepared to deal with all geometry types, but it has only been tested to work with
        # polygons, so I am turning the other layer types off
        #self.valid_layer_types = point_types + line_types + poly_types + multi_poly + multi_line + multi_point
        self.valid_layer_types = poly_types + multi_poly


        self.fromlayer.currentIndexChanged.connect(partial(self.reload_fields,'from'))
        self.tolayer.currentIndexChanged.connect(partial(self.reload_fields,'to'))
        self.OK.clicked.connect(self.run)

        # We load the node and area layers existing in our canvas
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if layer.wkbType() in self.valid_layer_types:
                self.fromlayer.addItem(layer.name())
                self.tolayer.addItem(layer.name())

    def reload_fields(self, box):
        if box == 'from':
            self.fromfield.clear()
            if self.fromlayer.currentIndex() >= 0:
                layer = getVectorLayerByName(self.fromlayer.currentText())  # If we have the right layer in hands
                for field in layer.pendingFields().toList():
                    self.fromfield.addItem(field.name())
        else:
            self.tofield.clear()
            if self.tolayer.currentIndex() >= 0:
                layer = getVectorLayerByName(self.tolayer.currentText())  # If we have the right layer in hands
                for field in layer.pendingFields().toList():
                    self.tofield.addItem(field.name())

    def runThread(self):
        QObject.connect(self.workerThread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.ProgressValueFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.ProgressRangeFromThread)

        QObject.connect(self.workerThread, SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"),
                        self.FinishedThreadedProcedure)
        self.OK.setEnabled(False)
        self.workerThread.start()
        self.exec_()

    def ProgressRangeFromThread(self, val):
        self.progressbar.setRange(0, val)

    def ProgressValueFromThread(self, value):
        self.progressbar.setValue(value)

    def FinishedThreadedProcedure(self, procedure):
        if self.workerThread.error is None:
            QgsMapLayerRegistry.instance().addMapLayer(self.workerThread.result)
        else:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", self.workerThread.error,
                                                      level=3)
        self.close()

    def run(self):
        error = None
        if self.fromlayer.currentIndex() < 0 or self.fromfield.currentIndex() < 0 or self.tolayer.currentIndex() < 0 or self.tofield.currentIndex() < 0:
            error = "ComboBox with ilegal value"

        flayer = self.fromlayer.currentText()
        ffield = self.fromfield.currentText()
        tlayer = self.tolayer.currentText()
        tfield = self.tofield.currentText()

        layer1 = getVectorLayerByName(self.fromlayer.currentText()).wkbType()
        layer2 = getVectorLayerByName(self.tolayer.currentText()).wkbType()
        if layer1 in point_types and layer2 in point_types:
            error = 'It is not sensible to have two point layers for this analysis'

        if error is None:
            self.workerThread = LeastCommonDenominator(qgis.utils.iface.mainWindow(), flayer, tlayer, ffield, tfield)
            self.runThread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly. ", error, level=3)

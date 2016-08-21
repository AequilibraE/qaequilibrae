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

from qgis.core import *
import qgis
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\\forms")

# For the GIS tools portion
from simple_tag_procedure import SimpleTAG
from ui_simple_tag import *
from global_parameters import *

#####################################################################################################
###################################        SIMPLE TAG          ######################################

class SimpleTagDialog(QtGui.QDialog, Ui_simple_tag):
    def __init__(self, iface):
        QtGui.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.valid_layer_types = point_types + line_types + poly_types

        self.fromtype = None
        self.frommatchingtype = None

        QObject.connect(self.fromlayer, SIGNAL("currentIndexChanged(QString)"), self.set_from_fields)
        QObject.connect(self.tolayer, SIGNAL("currentIndexChanged(QString)"), self.set_to_fields)
        QObject.connect(self.fromfield, SIGNAL("currentIndexChanged(QString)"), self.reload_fields)
        QObject.connect(self.matchingfrom, SIGNAL("currentIndexChanged(QString)"), self.reload_fields_matching)
        QObject.connect(self.needsmatching, SIGNAL("stateChanged(int)"), self.works_field_matching)

        self.OK.clicked.connect(self.run)

        # We load the node and area layers existing in our canvas
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if layer.wkbType() in self.valid_layer_types:
                self.fromlayer.addItem(layer.name())
                self.tolayer.addItem(layer.name())

        self.works_field_matching()

    def reload_fields(self):
        self.matches_types()
        self.set_to_fields()

    def reload_fields_matching(self):
        self.matches_types()
        if self.tolayer.currentIndex() >= 0:
            self.matchingto.clear()
            layer = getVectorLayerByName(self.tolayer.currentText())  # If we have the right layer in hands
            for field in layer.pendingFields().toList():
                #if self.frommatchingtype == field.type():
                self.matchingto.addItem(field.name())

    def set_from_fields(self):
        self.fromfield.clear()

        if self.fromlayer.currentIndex() >= 0:
            layer = getVectorLayerByName(self.fromlayer.currentText())  # If we have the right layer in hands

            for field in layer.pendingFields().toList():
                self.fromfield.addItem(field.name())

            self.enclosed.setEnabled(True)
            if layer.wkbType() not in poly_types:
                self.enclosed.setEnabled(False)
                if self.enclosed.isChecked:
                    self.touching.setChecked(True)

        if self.needsmatching.isChecked():
            self.works_field_matching()
        self.matches_types()

    def set_to_fields(self):
        self.tofield.clear()

        if self.tolayer.currentIndex() >= 0:
            layer = getVectorLayerByName(self.tolayer.currentText())  # If we have the right layer in hands

            for field in layer.pendingFields().toList():
                #if self.fromtype == field.type():
                self.tofield.addItem(field.name())
        if self.needsmatching.isChecked(): self.works_field_matching()

    def works_field_matching(self):

        self.matchingfrom.clear()
        self.matchingto.clear()

        if self.needsmatching.isChecked():
            self.matchingfrom.setVisible(True)
            self.matchingto.setVisible(True)
            self.lblmatchfrom.setVisible(True)
            self.lblmatchto.setVisible(True)

            if self.fromlayer.currentIndex() >= 0:
                layer = getVectorLayerByName(self.fromlayer.currentText())  # If we have the right layer in hands
                for field in layer.pendingFields().toList():
                    self.matchingfrom.addItem(field.name())

            if self.tolayer.currentIndex() >= 0:
                layer = getVectorLayerByName(self.tolayer.currentText())  # If we have the right layer in hands
                for field in layer.pendingFields().toList():
                    self.matchingto.addItem(field.name())
        else:
            self.matchingfrom.setVisible(False)
            self.matchingto.setVisible(False)
            self.lblmatchfrom.setVisible(False)
            self.lblmatchto.setVisible(False)

    def matches_types(self):
        self.fromtype = None
        self.frommatchingtype = None

        if self.fromlayer.currentIndex() >= 0:
            layer = getVectorLayerByName(self.fromlayer.currentText())  # If we have the right layer in hands
            for field in layer.pendingFields().toList():
                if self.fromfield.currentText() == field.name():
                    self.fromtype = field.type()

        if self.needsmatching.isChecked():
            if self.fromlayer.currentIndex() >= 0:
                layer = getVectorLayerByName(self.fromlayer.currentText())  # If we have the right layer in hands
                for field in layer.pendingFields().toList():
                    if self.matchingfrom.currentText() == field.name():
                        self.frommatchingtype = field.type()

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
        if self.workerThread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", self.workerThread.error,
                                                      level=3)
        self.close()

    def run(self):
        error = False
        if self.fromlayer.currentIndex() < 0 or self.fromfield.currentIndex() < 0 or self.tolayer.currentIndex() < 0 or self.tofield.currentIndex() < 0: error = True
        if self.needsmatching.isChecked():
            if self.matchingfrom.currentIndex() < 0 or self.matchingto.currentIndex() < 0: error = True

        flayer = self.fromlayer.currentText()
        ffield = self.fromfield.currentText()

        tlayer = self.tolayer.currentText()
        tfield = self.tofield.currentText()

        fmatch = None
        tmatch = None
        if self.needsmatching.isChecked():
            fmatch = self.matchingfrom.currentText()
            tmatch = self.matchingto.currentText()

        if self.enclosed.isChecked():
            operation = "ENCLOSED"
        elif self.touching.isChecked():
            operation = "TOUCHING"
        else:
            operation = "CLOSEST"

        if error == False:
            self.workerThread = SimpleTAG(qgis.utils.iface.mainWindow(), flayer, tlayer, ffield, tfield, fmatch,
                                           tmatch, operation)
            self.runThread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", '  Try again', level=3)

    def unload(self):
        if self.use_node_ids.isChecked():
            updates_a_b_nodes(self.linelayers.currentText(), self.nodelayers.currentText(),
                              self.node_fields.currentText())
        else:
            updates_a_b_nodes(self.linelayers.currentText(), new_layer=self.out_nodes.text)

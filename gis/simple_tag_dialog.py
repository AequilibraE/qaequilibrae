"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Compute GIS tags
 Purpose:    Loads GUI for computing GIS tags

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
 Updated:    30/10/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4.QtCore import *
from PyQt4 import QtGui, uic
import qgis
import sys
import os

# For the GIS tools portion
from simple_tag_procedure import SimpleTAG

from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import  get_vector_layer_by_name

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_simple_tag.ui'))

class SimpleTagDialog(QtGui.QDialog, FORM_CLASS):
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
            if 'wkbType' in dir(layer):
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
            layer = get_vector_layer_by_name(self.tolayer.currentText())  # If we have the right layer in hands
            for field in layer.pendingFields().toList():
                self.matchingto.addItem(field.name())

    def set_from_fields(self):
        self.fromfield.clear()

        if self.fromlayer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands

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
            layer = get_vector_layer_by_name(self.tolayer.currentText())  # If we have the right layer in hands

            for field in layer.pendingFields().toList():
                self.tofield.addItem(field.name())
        if self.needsmatching.isChecked():
            self.works_field_matching()

    def works_field_matching(self):

        self.matchingfrom.clear()
        self.matchingto.clear()

        if self.needsmatching.isChecked():
            self.matchingfrom.setVisible(True)
            self.matchingto.setVisible(True)
            self.lblmatchfrom.setVisible(True)
            self.lblmatchto.setVisible(True)

            if self.fromlayer.currentIndex() >= 0:
                layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands
                for field in layer.pendingFields().toList():
                    self.matchingfrom.addItem(field.name())

            if self.tolayer.currentIndex() >= 0:
                layer = get_vector_layer_by_name(self.tolayer.currentText())  # If we have the right layer in hands
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
            layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands
            for field in layer.pendingFields().toList():
                if self.fromfield.currentText() == field.name():
                    self.fromtype = field.type()

        if self.needsmatching.isChecked():
            if self.fromlayer.currentIndex() >= 0:
                layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands
                for field in layer.pendingFields().toList():
                    if self.matchingfrom.currentText() == field.name():
                        self.frommatchingtype = field.type()

    def run_thread(self):
        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.progress_range_from_thread)

        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.finished_threaded_procedure)
        self.OK.setEnabled(False)
        self.worker_thread.start()
        self.exec_()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def finished_threaded_procedure(self, procedure):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", self.worker_thread.error,
                                                      level=3)
        self.close()

    def run(self):
        error = False
        if min(self.fromlayer.currentIndex(), self.fromfield.currentIndex(),
               self.tolayer.currentIndex(), self.tofield.currentIndex()) < 0:
            error = True

        if self.needsmatching.isChecked():
            if self.matchingfrom.currentIndex() < 0 or self.matchingto.currentIndex() < 0:
                error = True

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

        if not error:
            self.worker_thread = SimpleTAG(qgis.utils.iface.mainWindow(), flayer, tlayer, ffield, tfield, fmatch,
                                           tmatch, operation)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", '  Try again', level=3)

    def unload(self):
        if self.use_node_ids.isChecked():
            updates_a_b_nodes(self.linelayers.currentText(), self.nodelayers.currentText(),
                              self.node_fields.currentText())
        else:
            updates_a_b_nodes(self.linelayers.currentText(), new_layer=self.out_nodes.text)

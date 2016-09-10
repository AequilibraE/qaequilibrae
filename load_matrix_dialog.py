"""
/***************************************************************************
 AequilibraE - www.AequilibraE.com

    Name:        Dialog for loading matrices from CSVs/DBFs loaded as layers
                              -------------------
        Creation           2016-08-15
        Update             2016-08-15
        copyright            : AequilibraE developers 2016
        Original Author: Pedro Camargo (c@margo.co)
        Contributors:
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""

from qgis.core import *
import qgis
from PyQt4 import QtGui
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import numpy as np

import sys, os
from functools import partial
from auxiliary_functions import *
from global_parameters import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/")

from load_matrix_class import LoadMatrix
from ui_matrix_loader import *

no_omx = False
try:
    import openmatrix as omx
except:
    no_omx = True

class LoadMatrixDialog(QtGui.QDialog, Ui_matrix_loader):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.layer = None
        self.orig = None
        self.dest = None
        self.cells = None
        self.matrix = None
        self.error = None

        self.radio_layer_matrix.clicked.connect(self.change_matrix_type)
        self.radio_npy_matrix.clicked.connect(self.change_matrix_type)
        self.radio_omx_matrix.clicked.connect(self.change_matrix_type)

        # For changing the network layer
        self.matrix_layer.currentIndexChanged.connect(self.load_fields_to_ComboBoxes)

        # For adding skims
        self.load.clicked.connect(self.load_the_matrix)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if layer.wkbType() == 100:
                self.matrix_layer.addItem(layer.name())

        if no_omx:
            self.radio_omx_matrix.setEnabled(False)

    def change_matrix_type(self):
        members = [self.lbl_matrix, self.lbl_from, self.matrix_layer, self.field_from]
        all_members = members + [self.lbl_to, self.lbl_flow, self.field_to, self.field_cells]

        # Covers the Numpy option (minimizes the code length this way)
        for member in all_members:
            member.setVisible(False)

        if self.radio_layer_matrix.isChecked():
            self.lbl_matrix.setText('Matrix')
            self.lbl_from.setText('From')
            for member in all_members:
                member.setVisible(True)

        if self.radio_omx_matrix.isChecked():
            self.lbl_matrix.setText('Matrix core')
            self.lbl_from.setText('Indices')
            for member in members:
                member.setVisible(True)

    def load_fields_to_ComboBoxes(self):

        for combo in [self.field_from, self.field_to, self.field_cells]:
            combo.clear()

        if self.matrix_layer.currentIndex() >= 0:
            self.layer = getVectorLayerByName(self.matrix_layer.currentText())
            for field in self.layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    self.field_from.addItem(field.name())
                    self.field_to.addItem(field.name())
                    self.field_cells.addItem(field.name())
                if field.type() in float_types:
                    self.field_cells.addItem(field.name())

    def runThread(self):

        QObject.connect(self.workerThread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.ProgressValueFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.ProgressRangeFromThread)
        QObject.connect(self.workerThread, SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"),
                        self.FinishedThreadedProcedure)

        self.workerThread.start()
        self.exec_()


    # VAL and VALUE have the following structure: (bar/text ID, value)
    def ProgressRangeFromThread(self, val):
        self.progressbar.setRange(0, val)

    def ProgressValueFromThread(self, val):
        self.progressbar.setValue(val)

    def FinishedThreadedProcedure(self, param):
        if self.workerThread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error while loading matrix:", self.workerThread.error,
                                                      level=1)
        else:
            self.matrix = self.workerThread.matrix
            self.ExitProcedure()

    def load_the_matrix(self):  # CREATING GRAPH
        self.error = None

        if self.radio_layer_matrix.isChecked():
            if self.field_from.currentIndex() < 0 or self.field_from.currentIndex() < 0 or self.field_cells.currentIndex() < 0:
                self.error = 'Invalid field chosen'

            if self.error is None:
                idx1 = self.layer.fieldNameIndex(self.field_from.currentText())
                idx2 = self.layer.fieldNameIndex(self.field_to.currentText())
                idx3 = self.layer.fieldNameIndex(self.field_cells.currentText())
                idx = [idx1, idx2, idx3]

                self.workerThread = LoadMatrix(qgis.utils.iface.mainWindow(), self.layer, idx)
                self.runThread()

        if self.radio_npy_matrix.isChecked():
            file_types = "NumPY array(*.npy)"
            newname = QFileDialog.getOpenFileName(None, 'Result file', self.path, file_types)
            try:
                matrix = np.load(newname)
                if len(matrix.shape[:]) == 2:
                    self.matrix = matrix
                    self.ExitProcedure()
                else:
                    self.error = 'Numpy array needs to be 2 dimensional. Matrix provided has ' + str(len(matrix.shape[:]))
            except:
                pass


        if self.radio_omx_matrix.isChecked():
            pass
            # Still not implemented

        if self.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1)

    def ExitProcedure(self):
        self.close()

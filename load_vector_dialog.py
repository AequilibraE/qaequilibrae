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

from load_vector_class import LoadVector
from ui_vector_loader import Ui_vector_loader

try:
    import omx
    OMX = True
except:
    OMX = False

class LoadVectorDialog(QtGui.QDialog, Ui_vector_loader):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.layer = None
        self.zones = None
        self.cells = None
        self.vector = None
        self.error = None

        self.radio_layer_matrix.clicked.connect(self.change_vector_type)
        self.radio_npy_matrix.clicked.connect(self.change_vector_type)
        self.radio_omx_matrix.clicked.connect(self.change_vector_type)

        # For changing the network layer
        self.vector_layer.currentIndexChanged.connect(self.load_fields_to_ComboBoxes)

        # For adding skims
        self.load.clicked.connect(self.load_the_vector)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if layer.wkbType() in [100] + point_types + poly_types:
                self.vector_layer.addItem(layer.name())

        if not OMX:
            self.radio_omx_matrix.setVisible(False)

    def change_vector_type(self):
        members = [self.lbl_matrix, self.lbl_from, self.vector_layer, self.field_from]
        all_members = members + [self.lbl_flow, self.field_cells]

        # Covers the Numpy option (minimizes the code length this way)
        for member in all_members:
            member.setVisible(False)

        if self.radio_layer_matrix.isChecked():
            self.lbl_matrix.setText('Vector layer')
            self.lbl_from.setText('From')
            for member in all_members:
                member.setVisible(True)

        if self.radio_omx_matrix.isChecked():
            self.lbl_matrix.setText('Vector core')
            self.lbl_from.setText('Indices')
            for member in members:
                member.setVisible(True)

    def load_fields_to_ComboBoxes(self):
        for combo in [self.field_from, self.field_cells]:
            combo.clear()

        if self.vector_layer.currentIndex() >= 0:
            self.layer = getVectorLayerByName(self.vector_layer.currentText())
            for field in self.layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    self.field_from.addItem(field.name())
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
            qgis.utils.iface.messageBar().pushMessage("Error while loading vector:", self.workerThread.error,
                                                      level=1)
        else:
            self.vector = self.workerThread.vector
            self.ExitProcedure()

    def load_the_vector(self):
        self.error = None

        if self.radio_layer_matrix.isChecked():
            if self.field_from.currentIndex() < 0 or self.field_from.currentIndex() < 0 or self.field_cells.currentIndex() < 0:
                self.error = 'Invalid field chosen'

            if self.error is None:
                idx1 = self.layer.fieldNameIndex(self.field_from.currentText())
                idx3 = self.layer.fieldNameIndex(self.field_cells.currentText())
                idx = [idx1, idx2, idx3]

                self.workerThread = LoadVector(qgis.utils.iface.mainWindow(), self.layer, idx)
                self.runThread()

        if self.radio_npy_matrix.isChecked():
            file_types = "NumPY array(*.npy)"
            newname = QFileDialog.getOpenFileName(None, 'Result file', self.path, file_types)
            try:
                vector = np.load(newname)
                if len(vector.shape[:]) == 1:
                    self.vector = vector
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

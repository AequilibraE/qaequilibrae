"""
/***************************************************************************
 AequilibraE - www.AequilibraE.com
 
    Name:        Dialogs for matrix manipulation tools
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys

from global_parameters import *

from auxiliary_functions import *
from NumpyModel import NumpyModel
from load_matrix_dialog import LoadMatrixDialog

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "//forms//")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "//algorithms//")

from desire_lines_procedure import DesireLinesProcedure
from ui_DesireLines import *

class DesireLinesDialog(QDialog, Ui_DesireLines):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.error = None
        self.validtypes = numeric_types
        self.tot_skims = 0
        self.name_skims = 0
        self.matrix = None
        self.path = standard_path()

        # FIRST, we connect slot signals
        # For changing the input matrix
        self.but_load_new_matrix.clicked.connect(self.find_matrices)

        self.zoning_layer.currentIndexChanged.connect(self.load_fields_to_ComboBoxes)


        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if layer.wkbType() in poly_types or layer.wkbType() in point_types:
                self.zoning_layer.addItem(layer.name())

    # Create desire lines
        self.create_dl.clicked.connect(self.run)

    def runThread(self):
        QObject.connect(self.workerThread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.ProgressValueFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressText( PyQt_PyObject )"), self.ProgressTextFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.ProgressRangeFromThread)
        QObject.connect(self.workerThread, SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"),
                        self.jobFinishedFromThread)
        self.workerThread.start()
        self.exec_()

    def load_fields_to_ComboBoxes(self):
        self.zone_id_field.clear()
        if self.zoning_layer.currentIndex() >= 0:
            layer = getVectorLayerByName(self.zoning_layer.currentText())
            for field in layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    self.zone_id_field.addItem(field.name())

    def add_matrix_to_viewer(self):
        """
            procedure to add the matrix to the viewer
        """
        if self.matrix is not None:
            self.rows = self.matrix.shape[0]
            self.columns = self.matrix.shape[1]

            # Load the matrix
            row_headers = []
            col_headers = []
            for i in range(self.rows):
                row_headers.append(str(i))
            for j in range(self.columns):
                col_headers.append(str(j))

            m = NumpyModel(self.matrix, col_headers, row_headers)
            self.matrix_viewer.setModel(m)

    def find_matrices(self):
        #if self.matrix is not None:
        #    self.lbl_matrix_loaded.setText('')

        dlg2 = LoadMatrixDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.matrix is not None:
            self.matrix = dlg2.matrix

        self.add_matrix_to_viewer()

    def ProgressRangeFromThread(self, val):
        self.progressbar.setRange(0, val[1])

    def ProgressValueFromThread(self, value):
        self.progressbar.setValue(value[1])

    def ProgressTextFromThread(self, value):
        self.progress_label.setText(value[1])

    def jobFinishedFromThread(self, success):
        if self.workerThread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Procedure error: ", self.workerThread.error, level=3)
        else:
            try:
                QgsMapLayerRegistry.instance().addMapLayer(self.workerThread.result_layer)
            except:
                pass
        self.ExitProcedure()

    def run(self):
        if self.matrix is not None:
            dl_type = 'DesireLines'
            if self.radio_delaunay.isChecked():
                dl_type = 'DelaunayLines'
            self.workerThread = DesireLinesProcedure(qgis.utils.iface.mainWindow(), self.zoning_layer.currentText(),
                                                        self.zone_id_field.currentText(), self.matrix, dl_type)
            self.runThread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Matrix not loaded", '', level=3)
    def ExitProcedure(self):
        self.close()

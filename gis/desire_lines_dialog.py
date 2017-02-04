"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loads GUI for creating desire lines
 Purpose:    Creatind desire and delaunay lines

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-01
 Updated:    2016-10-30
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

from global_parameters import *

from auxiliary_functions import *
from numpy_model import NumpyModel
from load_matrix_dialog import LoadMatrixDialog

from desire_lines_procedure import DesireLinesProcedure
from forms import Ui_DesireLines

no_binary = False
try:
    from aequilibrae.paths import all_or_nothing
except:
    no_binary = True
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
        self.rows = None
        self.columns = None

        # FIRST, we connect slot signals
        # For changing the input matrix
        self.but_load_new_matrix.clicked.connect(self.find_matrices)

        self.zoning_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)

        # Create desire lines
        self.create_dl.clicked.connect(self.run)

        # cancel button
        self.cancel.clicked.connect(self.exit_procedure)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if 'wkbType' in dir(layer):
                if layer.wkbType() in poly_types or layer.wkbType() in point_types:
                    self.zoning_layer.addItem(layer.name())

                    self.progress_label.setVisible(True)
                    self.progressbar.setVisible(True)

    def run_thread(self):
        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.job_finished_from_thread)
        self.worker_thread.start()
        self.exec_()

    def load_fields_to_combo_boxes(self):
        self.zone_id_field.clear()
        if self.zoning_layer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.zoning_layer.currentText())
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
        dlg2 = LoadMatrixDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.matrix is not None:
            self.matrix = dlg2.matrix

        self.add_matrix_to_viewer()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val[1])

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value[1])

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value[1])

    def job_finished_from_thread(self, success):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Procedure error: ", self.worker_thread.error, level=3)
        else:
            try:
                QgsMapLayerRegistry.instance().addMapLayer(self.worker_thread.result_layer)
            except:
                pass
        self.exit_procedure()

    def run(self):
        if self.matrix is not None:

            self.lbl_funding1.setVisible(False)
            self.lbl_funding2.setVisible(False)
            self.progress_label.setVisible(True)
            self.progressbar.setVisible(True)

            dl_type = 'DesireLines'
            if self.radio_delaunay.isChecked():
                dl_type = 'DelaunayLines'

            self.worker_thread = DesireLinesProcedure(qgis.utils.iface.mainWindow(), self.zoning_layer.currentText(),
                                                        self.zone_id_field.currentText(), self.matrix, dl_type)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Matrix not loaded", '', level=3)

    def exit_procedure(self):
        self.close()

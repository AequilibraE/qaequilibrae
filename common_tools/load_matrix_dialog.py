"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loads matrix from file/layer
 Purpose:    Loads GUI for loading matrix from different sources

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    2017-06-07
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4 import QtGui, uic
from scipy.sparse import coo_matrix
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import numpy as np

import sys
import os
from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *
from get_output_file_name import GetOutputFileName
from load_matrix_class import LoadMatrix, MatrixReblocking
from report_dialog import ReportDialog

no_omx = False
try:
    import openmatrix as omx
except:
    no_omx = True

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_matrix_loader.ui'))


class LoadMatrixDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, **kwargs):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.sparse = kwargs.get('sparse', False)
        self.multiple = kwargs.get('multiple', False)
        self.layer = None
        self.orig = None
        self.dest = None
        self.cells = None
        self.matrix_count = 0
        self.matrices = {}
        self.matrix = None
        self.error = None
        self.__current_name = None

        self.but_load.setEnabled(False)
        self.radio_layer_matrix.clicked.connect(self.change_matrix_type)
        self.radio_npy_matrix.clicked.connect(self.change_matrix_type)
        self.radio_omx_matrix.clicked.connect(self.change_matrix_type)

        # For changing the network layer
        self.matrix_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)

        # Buttons
        self.but_load.clicked.connect(self.load_the_matrix)
        self.but_save_for_single_use.clicked.connect(self.prepare_final_matrix)
        self.but_permanent_save.clicked.connect(self.find_place_to_save_matrix)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if 'wkbType' in dir(layer):
                if layer.wkbType() == 100:
                    self.matrix_layer.addItem(layer.name())

        if no_omx:
            self.radio_omx_matrix.setEnabled(False)

        if self.multiple:
            self.matrix_list_view.setColumnWidth(0, 100)
            self.matrix_list_view.setColumnWidth(1, 100)
            self.matrix_list_view.setColumnWidth(2, 125)
            self.matrix_list_view.itemChanged.connect(self.change_matrix_name)
        else:

            self.matrix_list_view.setVisible(False)
            self.resize(368, 233)

    def change_matrix_type(self):
        self.but_load.setEnabled(True)
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
            self.load_fields_to_combo_boxes()

        if self.radio_omx_matrix.isChecked():
            self.lbl_matrix.setText('Matrix core')
            self.lbl_from.setText('Indices')
            for member in members:
                member.setVisible(True)

    def load_fields_to_combo_boxes(self):
        self.but_load.setEnabled(False)
        for combo in [self.field_from, self.field_to, self.field_cells]:
            combo.clear()

        if self.matrix_layer.currentIndex() >= 0:
            self.but_load.setEnabled(True)
            self.layer = get_vector_layer_by_name(self.matrix_layer.currentText())
            for field in self.layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    self.field_from.addItem(field.name())
                    self.field_to.addItem(field.name())
                    self.field_cells.addItem(field.name())
                if field.type() in float_types:
                    self.field_cells.addItem(field.name())

    def run_thread(self):

        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.finished_threaded_procedure)

        self.but_load.setEnabled(False)
        self.but_save_for_single_use.setEnabled(False)
        self.but_permanent_save.setEnabled(False)
        self.worker_thread.start()
        self.exec_()

    # VAL and VALUE have the following structure: (bar/text ID, value)
    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, val):
        self.progressbar.setValue(val)

    def progress_text_from_thread(self, val):
        self.progress_label.setText(val)

    def finished_threaded_procedure(self, param):
        self.but_save_for_single_use.setEnabled(True)
        self.but_permanent_save.setEnabled(True)
        self.but_load.setEnabled(True)
        if self.worker_thread.report:
            dlg2 = ReportDialog(self.iface, self.worker_thread.report)
            dlg2.show()
            dlg2.exec_()
        else:
            if param == 'LOADED-MATRIX':
                self.matrices[self.__current_name] = self.worker_thread.matrix
                self.matrix_count += 1
                self.update_matrix_list()

                if self.multiple == False:
                    self.prepare_final_matrix()

            elif param == 'REBLOCKED MATRICES':
                self.matrix = self.worker_thread.matrix
                self.exit_procedure()


    def load_the_matrix(self):
        self.error = None
        self.worker_thread = None
        if self.radio_layer_matrix.isChecked():
            if self.field_from.currentIndex() < 0 or self.field_from.currentIndex() < 0 or self.field_cells.currentIndex() < 0:
                self.error = 'Invalid field chosen'

            if self.error is None:
                self.__current_name = self.matrix_layer.currentText().replace(" ", "_")
                idx1 = self.layer.fieldNameIndex(self.field_from.currentText())
                idx2 = self.layer.fieldNameIndex(self.field_to.currentText())
                idx3 = self.layer.fieldNameIndex(self.field_cells.currentText())
                idx = [idx1, idx2, idx3]

                self.worker_thread = LoadMatrix(qgis.utils.iface.mainWindow(), type='layer', layer=self.layer, idx=idx,
                                                sparse=self.sparse)

        if self.radio_npy_matrix.isChecked():
            file_types = ["NumPY array(*.npy)"]
            default_type = '.npy'
            box_name = 'Matrix Loader'
            new_name, type = GetOutputFileName(self, box_name, file_types, default_type, self.path)
            self.__current_name = new_name.replace(" ", "_")

            self.worker_thread = LoadMatrix(qgis.utils.iface.mainWindow(), type='numpy', file_path=new_name)

        if self.radio_omx_matrix.isChecked():
            pass
            # Still not implemented

        if self.worker_thread is not None:
            self.run_thread()

        if self.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1)

    def update_matrix_list(self):
        self.matrix_list_view.blockSignals(True)
        self.matrix_list_view.clearContents()
        self.matrix_list_view.setRowCount(self.matrix_count)

        i = 0
        for key, value in self.matrices.iteritems():
            r = int(np.max(value['from']))
            c = int(np.max(value['to']))
            dimensions = "{:,}".format(r) + " x " + "{:,}".format(c)
            total = "{:,.2f}".format(float(np.sum(value['flow'])))
            item_1 = QTableWidgetItem(key)
            self.matrix_list_view.setItem(i, 0, item_1)

            item_2 = QTableWidgetItem(dimensions)
            item_2.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.matrix_list_view.setItem(i, 1, item_2)

            item_3 = QTableWidgetItem(total)
            item_3.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.matrix_list_view.setItem(i, 2, item_3)

            i += 1
        self.matrix_list_view.blockSignals(False)

    def change_matrix_name(self, item):
        row = item.row()
        new_name = self.matrix_list_view.item(row, 0).text().replace(" ", "_")

        current_names = []
        for i in range(self.matrix_count):
            current_names.append(self.matrix_list_view.item(i, 0).text())

        for old_key in self.matrices.keys():
            if old_key not in current_names:
                self.matrices[new_name] = self.matrices.pop(old_key)
        self.update_matrix_list()

    def find_place_to_save_matrix(self):
        file_name, file_extension = GetOutputFileName(self, 'AequilibraeMatrix', ["Aequilibrae Matrix(*.aem)"], ".aem",
                                     self.path)

        file_path, file_name = os.path.split(file_name)

        self.prepare_final_matrix(path=file_path, file_name=file_name)

    def prepare_final_matrix(self, **kwargs):
        file_name = kwargs.get('file_name', None)
        file_path = kwargs.get('path', None)

        if file_name is None:
            self.worker_thread = MatrixReblocking(qgis.utils.iface.mainWindow(),
                                                  sparse=self.sparse, matrices=self.matrices)
        else:
            self.worker_thread = MatrixReblocking(qgis.utils.iface.mainWindow(), file_name=file_name,
                                                  sparse=self.sparse, matrices=self.matrices, path=file_path)

        self.run_thread()


    def exit_procedure(self):
        self.close()
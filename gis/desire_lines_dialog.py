"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loads GUI for creating desire lines
 Purpose:    Creating desire and delaunay lines

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-01
 Updated:    2017-06-25
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
import sys
import os

from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import *

from ..common_tools import NumpyModel
from ..matrix import LoadMatrixDialog
from ..common_tools import ReportDialog

from desire_lines_procedure import DesireLinesProcedure


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_DesireLines.ui'))

class DesireLinesDialog(QDialog, FORM_CLASS):
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
        self.zones = None
        self.columns = None
        self.matrix_hash =None

        self.resize(383, 385)
        self.setMaximumSize(QSize(383, 385))

        # FIRST, we connect slot signals
        # For changing the input matrix
        self.but_load_new_matrix.clicked.connect(self.find_matrices)

        self.zoning_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)

        self.chb_use_all_matrices.toggled.connect(self.set_show_matrices)


        # Create desire lines
        self.create_dl.clicked.connect(self.run)

        # cancel button
        self.cancel.clicked.connect(self.exit_procedure)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if 'wkbType' in dir(layer):
                if layer.wkbType() in poly_types or layer.wkbType() in point_types:
                    self.zoning_layer.addItem(layer.name())

                    self.progress_label.setVisible(False)
                    self.progressbar.setVisible(False)

    def set_show_matrices(self):
        self.tbl_array_cores.clear()
        if self.chb_use_all_matrices.isChecked():
            self.resize(383, 385)
            self.setMaximumSize(QSize(383, 385))
        else:
            self.setMaximumSize(QSize(710, 385))
            self.resize(710, 385)
            self.tbl_array_cores.setColumnWidth(0, 200)
            self.tbl_array_cores.setColumnWidth(1, 80)
            self.tbl_array_cores.setHorizontalHeaderLabels(["Matrix","Use?"])

            if self.matrix is not None:
                table = self.tbl_array_cores
                table.setRowCount(self.matrix.num_matrices)
                for i, mat in enumerate(self.matrix.names):
                    item1 = QTableWidgetItem(mat)
                    item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    table.setItem(i, 0, item1)

                    chb1 = QCheckBox()
                    chb1.setChecked(True)
                    chb1.setEnabled(True)
                    table.setCellWidget(i, 1, self.centers_item(chb1))

    def centers_item(self, item):
        cell_widget = QWidget()
        lay_out = QHBoxLayout(cell_widget)
        lay_out.addWidget(item)
        lay_out.setAlignment(Qt.AlignCenter)
        lay_out.setContentsMargins(0, 0, 0, 0)
        cell_widget.setLayout(lay_out)
        return cell_widget

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
                if field.type() in numeric_types:
                    self.zone_id_field.addItem(field.name())

    def find_matrices(self):
        dlg2 = LoadMatrixDialog(self.iface, sparse=True, multiple=True, single_use=True)
        dlg2.show()
        dlg2.exec_()
        if dlg2.matrix is not None:
            self.matrix = dlg2.matrix

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val[1])

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value[1])

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value[1])

    def job_finished_from_thread(self, success):
        if self.worker_thread.error is not None:
            self.exit_procedure()
            self.throws_error(self.worker_thread.error)

        else:
            try:
                QgsMapLayerRegistry.instance().addMapLayer(self.worker_thread.result_layer)
            except:
                self.worker_thread.report.append('Could not load desire lines to map')
            if self.worker_thread.report:
                dlg2 = ReportDialog(self.iface, self.worker_thread.report)
                dlg2.show()
                dlg2.exec_()
        self.exit_procedure()

    def check_all_inputs(self):
        if self.matrix is None:
            return False

        if self.zoning_layer.currentIndex() < 0:
            return False

        if self.zone_id_field.currentIndex() < 0:
            return False

        if self.chb_use_all_matrices.isChecked():
            matrix_cores_to_use = self.matrix.names
        else:
            matrix_cores_to_use = []
            for i, mat in enumerate(self.matrix.names):
                if self.tbl_array_cores.cellWidget(i, 1).findChildren(QCheckBox)[0].isChecked():
                    matrix_cores_to_use.append(mat)

        if len(matrix_cores_to_use) > 0:
            self.matrix.computational_view(matrix_cores_to_use)
        else:
            return False


    def run(self):
        if self.check_all_inputs():
        # Sets the visual of the tool
            self.lbl_funding1.setVisible(False)
            self.lbl_funding2.setVisible(False)
            self.progress_label.setVisible(True)
            self.progressbar.setVisible(True)

            self.resize(710, 444)
            self.setMaximumSize(QSize(710, 444))

            dl_type = 'DesireLines'
            if self.radio_delaunay.isChecked():
                dl_type = 'DelaunayLines'

            self.worker_thread = DesireLinesProcedure(qgis.utils.iface.mainWindow(), self.zoning_layer.currentText(),
                                                        self.zone_id_field.currentText(), self.matrix, self.matrix_hash, dl_type)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Inputs not loaded properly. You need the layer and at least one matrix core", '', level=3)

    def throws_error(self, error_message):
        error_message = ["*** ERROR ***", error_message]
        dlg2 = ReportDialog(self.iface, error_message)
        dlg2.show()
        dlg2.exec_()

    def exit_procedure(self):
        self.close()

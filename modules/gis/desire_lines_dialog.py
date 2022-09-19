import logging
import os

import pandas as pd

import qgis

from qgis.PyQt import uic, QtCore
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout, QCheckBox, QDialog
from qgis.core import QgsProject
from .desire_lines_procedure import DesireLinesProcedure
from ..common_tools import ReportDialog
from ..common_tools import standard_path, get_vector_layer_by_name
from ..common_tools.global_parameters import poly_types, numeric_types, point_types
from ..matrix_procedures import list_matrices

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_DesireLines.ui"))


class DesireLinesDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)
        self.error = None
        self.validtypes = numeric_types
        self.tot_skims = 0
        self.name_skims = 0
        self.matrix = None
        self.path = standard_path()
        self.zones = None
        self.columns = None
        self.matrix_hash = {}
        self.qgis_project = qgis_project
        if qgis_project.project is None:
            self.proj_matrices = pd.DataFrame([])
        else:
            self.proj_matrices = list_matrices(self.qgis_project.project.matrices.fldr)
        self.logger = logging.getLogger("AequilibraEGUI")

        self.resize(389, 385)

        self.zoning_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)
        self.chb_use_all_matrices.toggled.connect(self.set_show_matrices)

        # Create desire lines
        self.create_dl.clicked.connect(self.run)

        # cancel button
        self.cancel.clicked.connect(self.exit_procedure)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if "wkbType" in dir(layer):
                if layer.wkbType() in poly_types or layer.wkbType() in point_types:
                    self.zoning_layer.addItem(layer.name())
                    self.progress_label.setVisible(False)
                    self.progressbar.setVisible(False)

        self.list_matrices()
        self.set_show_matrices()

    def list_matrices(self):
        for idx, rec in self.proj_matrices.iterrows():
            if len(rec.WARNINGS) == 0:
                self.cob_matrices.addItem(rec["name"])
        for key in self.qgis_project.matrices.keys():
            self.cob_matrices.addItem(key)

    def set_matrix(self):
        if self.cob_matrices.currentIndex() < 0:
            self.matrix = None
            return

        if self.cob_matrices.currentText() in self.qgis_project.matrices:
            self.matrix = self.qgis_project.matrices[self.cob_matrices.currentText()]
            return
        self.matrix = self.qgis_project.project.matrices.get_matrix(self.cob_matrices.currentText())

    def set_show_matrices(self):
        self.tbl_array_cores.setVisible(not self.chb_use_all_matrices.isChecked())
        self.tbl_array_cores.clear()
        if self.chb_use_all_matrices.isChecked():
            self.resize(389, 385)
            return

        self.set_matrix()
        self.resize(950, 385)
        self.tbl_array_cores.setColumnWidth(0, 200)
        self.tbl_array_cores.setColumnWidth(1, 80)
        self.tbl_array_cores.setHorizontalHeaderLabels(["Matrix", "Use?"])

        if self.matrix is not None:
            table = self.tbl_array_cores
            table.setRowCount(self.matrix.cores)
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
        self.worker_thread.desire_lines.connect(self.signal_handler)
        self.worker_thread.start()
        self.exec_()

    def load_fields_to_combo_boxes(self):
        self.zone_id_field.clear()
        if self.zoning_layer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.zoning_layer.currentText())
            for field in layer.dataProvider().fields().toList():
                if field.type() in numeric_types:
                    self.zone_id_field.addItem(field.name())

    def signal_handler(self, val):
        # Signals that will come from traffic assignment
        if val[0] == "zones finalized":
            self.progressbar.setValue(val[1])
        elif val[0] == "text AoN":
            self.progress_label.setText(val[1])

        # Signals that will come from desire lines procedure
        elif val[0] == "job_size_dl":
            self.progressbar.setRange(0, val[1])
        elif val[0] == "jobs_done_dl":
            self.progressbar.setValue(val[1])
        elif val[0] == "text_dl":
            self.progress_label.setText(val[1])
        elif val[0] == "finished_desire_lines_procedure":
            self.job_finished_from_thread()

    def job_finished_from_thread(self):
        try:
            QgsProject.instance().addMapLayer(self.worker_thread.result_layer)
        except Exception as e:
            self.worker_thread.report.append("Could not load desire lines to map")
            self.logger.error(f"Could not load desire lines to map. {e.args}")
        if self.worker_thread.report:
            dlg2 = ReportDialog(self.iface, self.worker_thread.report)
            dlg2.show()
            dlg2.exec_()
        self.exit_procedure()

    def check_all_inputs(self):
        self.set_matrix()
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
            if len(matrix_cores_to_use) == 1:
                self.matrix.matrix_view = self.matrix.matrix_view.reshape((self.matrix.zones, self.matrix.zones, 1))
        else:
            return False

        # list of zones from the matrix
        self.zones = self.matrix.index[:]

        return True

    def run(self):
        if self.check_all_inputs():
            # Sets the visual of the tool
            self.progress_label.setVisible(True)
            self.progressbar.setVisible(True)
            self.setMaximumSize(QtCore.QSize(383, 444))
            self.resize(383, 444)

            dl_type = "DesireLines"
            if self.radio_delaunay.isChecked():
                dl_type = "DelaunayLines"

            self.worker_thread = DesireLinesProcedure(
                qgis.utils.iface.mainWindow(),
                self.zoning_layer.currentText(),
                self.zone_id_field.currentText(),
                self.matrix,
                self.matrix_hash,
                dl_type,
            )
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage(
                "Inputs not loaded properly. You need the layer and at least one matrix_procedures core", "", level=3
            )

    def throws_error(self, error_message):
        error_message = ["*** ERROR ***", error_message]
        dlg2 = ReportDialog(self.iface, error_message)
        dlg2.show()
        dlg2.exec_()

    def exit_procedure(self):
        self.close()

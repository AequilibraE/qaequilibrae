import importlib.util as iutil
import os

import numpy as np
from aequilibrae.matrix.aequilibrae_matrix import AequilibraeMatrix, CORE_NAME_MAX_LENGTH

import aequilibrae
import qgis
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem
from qaequilibrae.modules.matrix_procedures.load_matrix_class import LoadMatrix
from qaequilibrae.modules.matrix_procedures.mat_reblock import MatrixReblocking
from qaequilibrae.modules.common_tools.all_layers_from_toc import all_layers_from_toc
from qaequilibrae.modules.common_tools.auxiliary_functions import standard_path, get_vector_layer_by_name
from qaequilibrae.modules.common_tools.get_output_file_name import GetOutputFileName
from qaequilibrae.modules.common_tools.global_parameters import float_types, integer_types
from qaequilibrae.modules.common_tools.report_dialog import ReportDialog

spec = iutil.find_spec("openmatrix")
has_omx = spec is not None

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_matrix_loader.ui"))


# TODO: Add possibility to add a centroid list to guarantee the match between matrix index and graph
# TODO: Allow user to import multiple matrices from CSV at once (like an export from TransCad or FAF data)
# TODO: Add a remove button to the list of matrices to be loaded. Remove double-click
class LoadMatrixDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, **kwargs):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.sparse = kwargs.get("sparse", False)
        self.multiple = kwargs.get("multiple", True)
        self.allow_single_use = kwargs.get("single_use", False)
        self.output_name = None
        self.layer = None
        self.orig = None
        self.dest = None
        self.cells = None
        self.matrix_count = 0
        self.matrices = {}
        self.matrix = AequilibraeMatrix()
        self.error = None
        self.__current_name = None
        self.logger = aequilibrae.logger

        # For changing the network layer
        self.matrix_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)

        # Buttons
        self.but_load.clicked.connect(self.load_the_matrix)

        if self.allow_single_use:
            self.but_save_for_single_use.clicked.connect(self.prepare_final_matrix)
        else:
            self.but_save_for_single_use.setVisible(False)

        self.but_permanent_save.clicked.connect(self.get_name_and_save_to_disk)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in all_layers_from_toc():  # We iterate through all layers
            if "wkbType" in dir(layer):
                if layer.wkbType() == 100:
                    self.matrix_layer.addItem(layer.name())

        self.resizing()

    def resizing(self):
        self.group_combo.setVisible(True)
        self.group_list.setVisible(True)
        self.group_buttons.setVisible(True)
        self.matrix_list_view.setColumnWidth(0, 180)
        self.matrix_list_view.setColumnWidth(1, 100)
        self.matrix_list_view.setColumnWidth(2, 125)
        self.matrix_list_view.itemChanged.connect(self.change_matrix_name)
        self.matrix_list_view.doubleClicked.connect(self.slot_double_clicked)
        self.setMaximumSize(QtCore.QSize(100000, 100000))
        self.resize(542, 427)
        self.but_permanent_save.setVisible(True)

        self.but_save_for_single_use.setEnabled(False)
        self.but_permanent_save.setEnabled(False)

    def slot_double_clicked(self, mi):
        row = mi.row()
        if row > -1:
            self.matrix_count -= 1
            mat_to_remove = self.matrix_list_view.item(row, 0).text()
            self.matrices.pop(mat_to_remove, None)
            self.update_matrix_list()

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
        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.ProgressText.connect(self.progress_text_from_thread)
        self.worker_thread.finished_threaded_procedure.connect(self.finished_threaded_procedure)

        self.but_load.setEnabled(False)
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
        self.but_load.setEnabled(True)
        if self.worker_thread.report:
            dlg2 = ReportDialog(self.iface, self.worker_thread.report)
            dlg2.show()
            dlg2.exec_()
        else:
            if param == "LOADED-MATRIX":
                self.compressed.setVisible(True)
                self.progress_label.setVisible(False)

                if self.__current_name in self.matrices.keys():
                    i = 1
                    while self.__current_name + "_" + str(i) in self.matrices.keys():
                        i += 1
                    self.__current_name = self.__current_name + "_" + str(i)

                self.matrices[self.__current_name] = self.worker_thread.matrix
                self.matrix_count += 1
                self.update_matrix_list()

                if not self.multiple:
                    self.update_matrix_hashes()

            elif param == "REBLOCKED MATRICES":
                self.matrix = self.worker_thread.matrix
                if self.compressed.isChecked():
                    pass
                    # compression not implemented yet
                self.exit_procedure()

    def __create_appropriate_name(self, nm: str) -> str:
        nm = nm.replace(" ", "_")
        if len(nm) > CORE_NAME_MAX_LENGTH - 3:
            nm = nm[:47]

        return nm

    def load_the_matrix(self):
        self.has_errors()

        if self.worker_thread is not None:
            self.run_thread()

        if self.error is not None:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Error:"), self.error, level=1)

    def update_matrix_list(self):
        if self.matrix_count > 0:
            self.but_save_for_single_use.setEnabled(True)
            self.but_permanent_save.setEnabled(True)
        else:
            self.but_save_for_single_use.setEnabled(False)
            self.but_permanent_save.setEnabled(False)

        self.matrix_list_view.clearContents()
        self.matrix_list_view.setRowCount(self.matrix_count)

        self.matrix_list_view.blockSignals(True)
        i = 0
        for key, value in self.matrices.items():
            r = np.unique(value["from"]).shape[0]
            c = np.unique(value["to"]).shape[0]
            dimensions = "{:,}".format(r) + " x " + "{:,}".format(c)
            total = "{:,.2f}".format(float(value["flow"].sum()))
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
        self.matrix_list_view.blockSignals(True)
        row = item.row()
        new_name = self.matrix_list_view.item(row, 0).text().lower().replace(" ", "_")
        item_1 = QTableWidgetItem(new_name)
        self.matrix_list_view.setItem(row, 0, item_1)

        current_names = []
        for i in range(self.matrix_count):
            current_names.append(self.matrix_list_view.item(i, 0).text())

        for old_key in self.matrices.keys():
            if old_key not in current_names:
                self.matrices[new_name] = self.matrices.pop(old_key)
        self.matrix_list_view.blockSignals(False)

    def get_name_and_save_to_disk(self):
        self.output_name, _ = GetOutputFileName(
            self, "AequilibraE matrix", ["Aequilibrae Matrix(*.aem)"], ".aem", self.path
        )
        self.prepare_final_matrix()

    def prepare_final_matrix(self):
        self.compressed.setVisible(False)
        self.progress_label.setVisible(True)

        self.build_worker_thread()

        self.run_thread()

    def exit_procedure(self):
        self.close()

    def build_worker_thread(self):
        if self.output_name is None:
            self.worker_thread = MatrixReblocking(
                qgis.utils.iface.mainWindow(), sparse=self.sparse, matrices=self.matrices
            )
        else:
            self.worker_thread = MatrixReblocking(
                qgis.utils.iface.mainWindow(), sparse=self.sparse, matrices=self.matrices, file_name=self.output_name
            )

    def has_errors(self):
        self.error = None
        self.worker_thread = None
        if (
            self.field_from.currentIndex() < 0
            or self.field_from.currentIndex() < 0
            or self.field_cells.currentIndex() < 0
        ):
            self.error = self.tr("Invalid field chosen")

        if self.error is None:
            self.compressed.setVisible(False)
            self.progress_label.setVisible(True)
            self.__current_name = self.__create_appropriate_name(self.field_cells.currentText().lower())
            idx1 = self.layer.dataProvider().fieldNameIndex(self.field_from.currentText())
            idx2 = self.layer.dataProvider().fieldNameIndex(self.field_to.currentText())
            idx3 = self.layer.dataProvider().fieldNameIndex(self.field_cells.currentText())
            idx = [idx1, idx2, idx3]

            self.worker_thread = LoadMatrix(
                qgis.utils.iface.mainWindow(), type="layer", layer=self.layer, idx=idx, sparse=self.sparse
            )
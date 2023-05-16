import os
from functools import partial

import qgis
from aequilibrae.matrix import AequilibraeData

from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem
from .load_dataset_class import LoadDataset
from ..common_tools.all_layers_from_toc import all_layers_from_toc
from ..common_tools.auxiliary_functions import standard_path, get_vector_layer_by_name
from ..common_tools.get_output_file_name import GetOutputFileName
from ..common_tools.global_parameters import integer_types, float_types, point_types, poly_types

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_vector_loader.ui"))


class LoadDatasetDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, single_use=True):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.output_name = None
        self.layer = None
        self.zones = None
        self.cells = None
        self.error = None
        self.selected_fields = None
        self.worker_thread = None
        self.dataset = None
        self.ignore_fields = []
        self.single_use = single_use

        self.radio_layer_matrix.clicked.connect(partial(self.size_it_accordingly, False))
        self.radio_aequilibrae.clicked.connect(partial(self.size_it_accordingly, False))
        self.chb_all_fields.clicked.connect(self.set_tables_with_fields)
        self.but_adds_to_links.clicked.connect(self.append_to_list)

        # For changing the network layer
        self.cob_data_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)
        self.but_removes_from_links.clicked.connect(self.removes_fields)
        # For adding skims
        self.but_load.clicked.connect(self.load_from_aequilibrae_format)
        self.but_save_and_use.clicked.connect(self.load_the_vector)
        self.but_import_and_use.clicked.connect(self.load_just_to_use)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in all_layers_from_toc():  # We iterate through all layers
            if "wkbType" in dir(layer):
                if layer.wkbType() in [100] + point_types + poly_types:
                    self.cob_data_layer.addItem(layer.name())

        if not self.single_use:
            self.radio_layer_matrix.setChecked(True)
            self.radio_aequilibrae.setEnabled(False)
            self.but_import_and_use.setEnabled(False)
            self.but_load.setEnabled(False)
            self.but_save_and_use.setText("Import")

        self.size_it_accordingly(partial(self.size_it_accordingly, False))

    def set_tables_with_fields(self):
        self.size_it_accordingly(False)

        if self.chb_all_fields.isChecked() and self.layer is not None:
            self.ignore_fields = []
            self.selected_fields = [x.name() for x in self.layer.dataProvider().fields().toList()]

        for table in [self.table_all_fields, self.table_fields_to_import]:
            table.setRowCount(0)
            table.clearContents()
        if self.layer is not None:
            comb = [(self.table_fields_to_import, self.selected_fields), (self.table_all_fields, self.ignore_fields)]
            for table, fields in comb:
                for field in fields:
                    table.setRowCount(table.rowCount() + 1)
                    item1 = QTableWidgetItem(field)
                    item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    table.setItem(table.rowCount() - 1, 0, item1)

    def size_it_accordingly(self, final=False):
        def set_size(w, h):
            self.setMaximumSize(QtCore.QSize(w, h))
            self.resize(w, h)

        if self.radio_aequilibrae.isChecked():
            set_size(154, 100)
        else:
            if final:
                if self.radio_layer_matrix.isChecked():
                    if self.chb_all_fields.isChecked():
                        set_size(498, 120)
                    self.progressbar.setMinimumHeight(100)
                else:
                    set_size(498, 410)
                    self.progressbar.setMinimumHeight(390)
            else:
                if self.chb_all_fields.isChecked():
                    set_size(449, 120)
                else:
                    set_size(449, 410)

    def removes_fields(self):
        for i in self.table_fields_to_import.selectedRanges():
            old_fields = [
                self.table_fields_to_import.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)
            ]

            self.ignore_fields.extend(old_fields)
            self.selected_fields = [x for x in self.selected_fields if x not in old_fields]

        self.set_tables_with_fields()

    def append_to_list(self):
        for i in self.table_all_fields.selectedRanges():
            new_fields = [self.table_all_fields.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            self.selected_fields.extend(new_fields)
            self.ignore_fields = [x for x in self.ignore_fields if x not in new_fields]

        self.set_tables_with_fields()

    def load_fields_to_combo_boxes(self):
        self.cob_index_field.clear()

        all_fields = []
        if self.cob_data_layer.currentIndex() >= 0:
            self.ignore_fields = []
            self.layer = get_vector_layer_by_name(self.cob_data_layer.currentText())
            self.selected_fields = [x.name() for x in self.layer.dataProvider().fields().toList()]
            for field in self.layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    self.cob_index_field.addItem(field.name())
                    all_fields.append(field.name())
                if field.type() in float_types:
                    all_fields.append(field.name())
        self.set_tables_with_fields()

    def run_thread(self):
        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.finished_threaded_procedure.connect(self.finished_threaded_procedure)

        self.chb_all_fields.setEnabled(False)
        self.but_load.setEnabled(False)
        self.but_save_and_use.setEnabled(False)
        self.worker_thread.start()
        self.exec_()

    # VAL and VALUE have the following structure: (bar/text ID, value)
    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, val):
        self.progressbar.setValue(val)

    def finished_threaded_procedure(self, param):
        self.but_load.setEnabled(True)
        self.but_save_and_use.setEnabled(True)
        self.chb_all_fields.setEnabled(True)
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error while loading vector:", self.worker_thread.error, level=1)
        else:
            self.dataset = self.worker_thread.output
        self.exit_procedure()

    def load_from_aequilibrae_format(self):
        out_name, _ = GetOutputFileName(self, "AequilibraE dataset", ["Aequilibrae dataset(*.aed)"], ".aed", self.path)
        try:
            self.dataset = AequilibraeData()
            self.dataset.load(out_name)
        except Exception as e:
            self.error = f"Could not load file. It might be corrupted or not a valid AequilibraE file. {e.args}"
        self.exit_procedure()

    def load_the_vector(self):
        if self.single_use:
            self.output_name = None
        else:
            self.error = None
            self.output_name, _ = GetOutputFileName(
                self, "AequilibraE dataset", ["Aequilibrae dataset(*.aed)"], ".aed", self.path
            )
            if self.output_name is None:
                self.error = "No name provided for the output file"

        if self.radio_layer_matrix.isChecked() and self.error is None:
            if self.cob_data_layer.currentIndex() < 0 or self.cob_index_field.currentIndex() < 0:
                self.error = "Invalid field chosen"

            index_field = self.cob_index_field.currentText()
            if index_field in self.selected_fields:
                self.selected_fields.remove(index_field)

            if len(self.selected_fields) > 0:
                self.worker_thread = LoadDataset(
                    qgis.utils.iface.mainWindow(),
                    layer=self.layer,
                    index_field=index_field,
                    fields=self.selected_fields,
                    file_name=self.output_name,
                )
                self.size_it_accordingly(True)
                self.run_thread()
            else:
                qgis.utils.iface.messageBar().pushMessage(
                    "Error:", "One cannot load a dataset with indices only", level=1
                )
        if self.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1)

    def load_just_to_use(self):
        self.single_use = True
        self.load_the_vector()

    def exit_procedure(self):
        self.close()

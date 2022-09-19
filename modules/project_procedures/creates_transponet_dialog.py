import os
import sys
from functools import partial
from os.path import isdir, join

from PyQt5.QtCore import Qt
from aequilibrae.project.network.network import Network

import qgis
from aequilibrae.parameters import Parameters
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QWidget, QFileDialog
from .creates_transponet_procedure import CreatesTranspoNetProcedure
from ..common_tools import ReportDialog
from ..common_tools import all_layers_from_toc
from ..common_tools import get_vector_layer_by_name, standard_path
from ..common_tools.global_parameters import point_types, line_types

sys.modules["qgsmaplayercombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_transponet_construction.ui"))


class CreatesTranspoNetDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgisproject):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgisproject.iface
        self.project = qgisproject
        self.setupUi(self)

        self.missing_data = -1
        self.path = standard_path()

        self.required_fields_links = Network.req_link_flds

        self.required_fields_nodes = Network.req_node_flds

        self.link_layer = False
        self.node_layer = False
        self.but_create_network_file.clicked.connect(self.create_net)
        self.but_choose_folder.clicked.connect(self.choose_folder)
        self.counter = {}
        self.proj_folder = False
        self.error = None
        self.node_layers_list.currentIndexChanged.connect(partial(self.changed_layer, "nodes"))

        self.link_layers_list.currentIndexChanged.connect(partial(self.changed_layer, "links"))
        self.node_fields = []
        self.link_fields = []
        self.node_field_indices = {}
        self.link_field_indices = {}
        self.report = None

        for layer in all_layers_from_toc():  # We iterate through all layers
            if "wkbType" in dir(layer):
                if layer.wkbType() in line_types:
                    self.link_layers_list.addItem(layer.name())

                if layer.wkbType() in point_types:
                    self.node_layers_list.addItem(layer.name())

        if self.node_layers_list.currentIndex() >= 0:
            self.changed_layer("nodes")
        if self.link_layers_list.currentIndex() >= 0:
            self.changed_layer("links")

        self.progressbar.setVisible(False)
        self.progress_label.setVisible(False)

        self.table_available_link_fields.setColumnWidth(0, 150)
        self.table_link_fields.setColumnWidth(0, 120)
        self.table_link_fields.setColumnWidth(1, 60)
        self.table_link_fields.setColumnWidth(2, 130)

        self.table_available_node_field.setColumnWidth(0, 150)
        self.table_node_fields.setColumnWidth(0, 120)
        self.table_node_fields.setColumnWidth(1, 60)
        self.table_node_fields.setColumnWidth(2, 130)

        self.but_adds_to_links.clicked.connect(partial(self.append_to_list, "links"))
        self.but_adds_to_nodes.clicked.connect(partial(self.append_to_list, "nodes"))

        self.but_removes_from_links.clicked.connect(partial(self.removes_fields, "links"))
        self.but_removes_from_nodes.clicked.connect(partial(self.removes_fields, "nodes"))

    def removes_fields(self, layer_type):
        layer_fields, table, final_table, required_fields = self.__find_layer_changed(layer_type)

        for i in final_table.selectedRanges():
            old_fields = [final_table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                if final_table.item(row, 0).text() in required_fields:
                    break
                final_table.removeRow(row)

            counter = table.rowCount()
            for field in old_fields:
                if field not in required_fields:
                    table.setRowCount(counter + 1)
                    item1 = QtWidgets.QTableWidgetItem(field)
                    item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    table.setItem(counter, 0, item1)
                    counter += 1

    def append_to_list(self, layer_type):
        layer_fields, table, final_table, required_fields = self.__find_layer_changed(layer_type)
        for i in table.selectedRanges():
            new_fields = [table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                table.removeRow(row)

            counter = final_table.rowCount()
            for field in new_fields:
                final_table.setRowCount(counter + 1)
                item1 = QtWidgets.QTableWidgetItem(field)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                final_table.setItem(counter, 0, item1)

                chb1 = QtWidgets.QCheckBox()
                chb1.setChecked(False)
                chb1.setEnabled(False)
                chb1.stateChanged.connect(self.keep_checked)
                final_table.setCellWidget(counter, 1, self.centers_item(chb1))

                cbb = QtWidgets.QComboBox()
                cbb.addItem(field)
                final_table.setCellWidget(counter, 2, self.centers_item(cbb))
                counter += 1

    def keep_checked(self):
        ch_box = self.sender()
        ch_box.setChecked(True)

    def __find_layer_changed(self, layer_type):
        layer_fields = None
        p = Parameters()

        def fkey(f):
            return list(f.keys())[0]

        if layer_type == "nodes":
            table = self.table_available_node_field
            final_table = self.table_node_fields
            # TODO : Change for the method .currentlayer()
            # Repeat the change throughout
            self.node_layer = get_vector_layer_by_name(self.node_layers_list.currentText())
            required_fields = self.required_fields_nodes
            if self.node_layer:
                layer_fields = self.node_layer.fields()
                layer_fields = [f for f in layer_fields if f.name().lower() not in Network.protected_fields]

            flds = p.parameters["network"]["nodes"]["fields"]
            ndflds = [f"{fkey(f)}" for f in flds if fkey(f).lower() not in Network.req_node_flds]
            required_fields.extend(ndflds)

        if layer_type == "links":
            table = self.table_available_link_fields
            final_table = self.table_link_fields
            self.link_layer = get_vector_layer_by_name(self.link_layers_list.currentText())
            required_fields = self.required_fields_links

            fields = p.parameters["network"]["links"]["fields"]
            flds = fields["one-way"]

            owlf = [f"{fkey(f)}" for f in flds if fkey(f).lower() not in Network.req_link_flds]

            flds = fields["two-way"]
            twlf = []
            for f in flds:
                twlf.extend([f"{fkey(f)}_ab", f"{fkey(f)}_ba"])

            required_fields = required_fields + owlf + twlf

            if self.link_layer:
                layer_fields = self.link_layer.fields()
                layer_fields = [f for f in layer_fields if f.name().lower() not in Network.protected_fields]

        return layer_fields, table, final_table, required_fields

    def changed_layer(self, layer_type):
        try:
            layer_fields, table, final_table, required_fields = self.__find_layer_changed(layer_type)
            table.clearContents()
            table.setRowCount(0)
            # We create the comboboxes that will hold the definitions for all the fields that are mandatory for
            # creating the appropriate triggers on the SQLite file
            if layer_fields is not None:
                fields = [field.name() for field in layer_fields]
                counter = 0
                for field in fields:
                    table.setRowCount(counter + 1)
                    item1 = QtWidgets.QTableWidgetItem(field)
                    item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    table.setItem(counter, 0, item1)
                    counter += 1
                self.counter[layer_type] = counter

            final_table.clearContents()
            final_table.setRowCount(0)

            counter = 0
            if layer_type == "links":
                init_fields = [x for x in required_fields if x not in Network.req_link_flds]
            else:
                init_fields = [x for x in required_fields if x not in Network.req_node_flds]

            for rf in required_fields:
                final_table.setRowCount(counter + 1)

                item1 = QtWidgets.QTableWidgetItem(rf)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                final_table.setItem(counter, 0, item1)

                chb1 = QtWidgets.QCheckBox()
                if rf in init_fields:
                    chb1.setChecked(True)
                    chb1.stateChanged.connect(partial(self.set_field_to_default, layer_type))
                else:
                    chb1.setChecked(True)
                    chb1.stateChanged.connect(partial(self.set_field_to_default, layer_type))
                    chb1.setChecked(False)
                    chb1.setEnabled(False)
                final_table.setCellWidget(counter, 1, self.centers_item(chb1))
                counter += 1
        except Exception as e:
            self.logger.error(e.args)

    def centers_item(self, item):
        cell_widget = QtWidgets.QWidget()
        lay_out = QtWidgets.QHBoxLayout(cell_widget)
        lay_out.addWidget(item)
        lay_out.setAlignment(Qt.AlignCenter)
        lay_out.setContentsMargins(0, 0, 0, 0)
        cell_widget.setLayout(lay_out)
        return cell_widget

    def set_field_to_default(self, layer_type):
        layer_fields, table, final_table, required_fields = self.__find_layer_changed(layer_type)

        if layer_fields is not None:
            ch_box = self.sender()
            parent = ch_box.parent()
            for i in range(final_table.rowCount()):
                if final_table.cellWidget(i, 1) is parent:
                    row = i
                    break

            if ch_box.isChecked():
                final_table.setCellWidget(row, 2, QtWidgets.QWidget())
            else:
                cbb = QtWidgets.QComboBox()
                for i in layer_fields:
                    cbb.addItem(i.name())
                final_table.setCellWidget(row, 2, self.centers_item(cbb))

    def choose_folder(self):
        self.proj_folder = QFileDialog.getExistingDirectory(QWidget(), "Parent folder", self.path)
        if self.proj_folder is None or len(self.proj_folder) == 0:
            return
        new_folder = "new_project"
        counter = 1
        while isdir(join(self.proj_folder, new_folder)):
            new_folder = f"new_project_{counter}"
            counter += 1

        self.proj_folder = join(self.proj_folder, new_folder)
        self.project_destination.setText(self.proj_folder)

    def create_net(self):

        ok, msg = self.check_data()

        if not ok:
            self.iface.messageBar().pushMessage("Error", msg, level=3, duration=10)
            return

        self.proj_folder = self.project_destination.text()
        if isdir(self.proj_folder):
            counter = 1
            while isdir(join(f"{self.proj_folder}{counter}")):
                counter += 1
            self.proj_folder = f"{self.proj_folder}{counter}"

        self.assembles_data()

        parameters = [self.proj_folder, self.node_layer, self.node_fields, self.link_layer, self.link_fields]

        self.but_create_network_file.setVisible(False)
        self.progressbar.setVisible(True)
        self.progress_label.setVisible(True)
        self.worker_thread = CreatesTranspoNetProcedure(qgis.utils.iface.mainWindow(), *parameters)
        self.run_thread()

    def check_data(self):
        if self.link_layer:
            if len(self.link_layer.crs().authid()) == 0:
                return False, "Link Layer has NO defined CRS"

        if self.node_layer:
            if len(self.node_layer.crs().authid()) == 0:
                return False, "Node Layer has NO defined CRS"

        return True, ""

    def assembles_data(self):
        def compile_fields(layer, table):
            fields = {}
            for row in range(table.rowCount()):
                f = table.item(row, 0).text()
                if table.cellWidget(row, 1).findChildren(QtWidgets.QCheckBox)[0].isChecked():
                    val = -1
                else:
                    widget = table.cellWidget(row, 2).findChildren(QtWidgets.QComboBox)[0]
                    source_name = widget.currentText()
                    val = layer.dataProvider().fieldNameIndex(source_name)
                fields[f] = val

            return fields

        self.node_fields = compile_fields(self.node_layer, self.table_node_fields)
        self.link_fields = compile_fields(self.link_layer, self.table_link_fields)

    def exit_procedure(self):
        self.close()

    def run_thread(self):
        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressText.connect(self.progress_text_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.jobFinished.connect(self.job_finished_from_thread)
        self.worker_thread.start()
        self.show()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value)

    def job_finished_from_thread(self, success):
        if self.worker_thread.report:
            dlg2 = ReportDialog(self.iface, self.worker_thread.report)
            dlg2.show()
            dlg2.exec_()
        self.exit_procedure()

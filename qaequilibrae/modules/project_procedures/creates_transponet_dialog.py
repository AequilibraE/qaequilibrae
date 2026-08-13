import sys
from functools import partial
from os.path import dirname, isdir, join

import qgis
from qgis.PyQt.QtCore import Qt
from aequilibrae.context import get_logger
from aequilibrae.project.network.network import Network
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QWidget, QFileDialog

from qaequilibrae.modules.common_tools import LiveLogBridge, ReportDialog, connect_progress_widgets
from qaequilibrae.modules.common_tools import all_layers_from_toc
from qaequilibrae.modules.common_tools import get_vector_layer_by_name, standard_path
from qaequilibrae.modules.common_tools.global_parameters import point_types, line_types
from qaequilibrae.modules.project_procedures.creates_transponet_procedure import CreatesTranspoNetProcedure

sys.modules["qgsmaplayercombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_transponet_construction.ui"))

# Fields of the standard AequilibraE link and node layers. Any other field is up to the user to bring from
# the layer being imported
extra_link_fields = ["name", "speed_ab", "speed_ba", "travel_time_ab", "travel_time_ba", "capacity_ab", "capacity_ba"]
standard_link_fields = Network.req_link_flds + extra_link_fields
standard_node_fields = Network.req_node_flds + ["modes", "link_types"]

# Fields computed by the project's triggers, so they can never be brought from the layer
computed_link_fields = ["a_node", "b_node", "distance"]
computed_node_fields = ["modes", "link_types"]

# Fields AequilibraE requires, but that QAequilibraE can populate on its own
initializable_link_fields = ["link_id"]


class CreatesTranspoNetDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.logger = get_logger()
        self.iface = qgis_project.iface
        self.qgis_project = qgis_project
        self.setupUi(self)

        self.missing_data = -1
        self.path = standard_path()

        # We list the standard layers, minus whatever the project computes on its own
        self.standard_fields_links = [fld for fld in standard_link_fields if fld not in computed_link_fields]
        self.standard_fields_nodes = [fld for fld in standard_node_fields if fld not in computed_node_fields]

        # The fields AequilibraE requires are taken from the layer. The remaining standard ones start out
        # initialized, as most layers being imported will not have them
        self.from_layer_links = [fld for fld in Network.req_link_flds if fld not in computed_link_fields]
        self.from_layer_nodes = [fld for fld in Network.req_node_flds if fld not in computed_node_fields]

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
        self.progress_bridge = LiveLogBridge()
        connect_progress_widgets(self.progress_bridge, self.progressbar, self.progress_label)

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
        layer_fields, table, final_table, standard_fields = self.__find_layer_changed(layer_type)

        for i in final_table.selectedRanges():
            old_fields = [final_table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                if final_table.item(row, 0).text() in standard_fields:
                    break
                final_table.removeRow(row)

            counter = table.rowCount()
            for field in old_fields:
                if field not in standard_fields:
                    table.setRowCount(counter + 1)
                    item1 = QtWidgets.QTableWidgetItem(field)
                    item1.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    table.setItem(counter, 0, item1)
                    counter += 1

    def append_to_list(self, layer_type):
        layer_fields, table, final_table, standard_fields = self.__find_layer_changed(layer_type)
        for i in table.selectedRanges():
            new_fields = [table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                table.removeRow(row)

            counter = final_table.rowCount()
            for field in new_fields:
                final_table.setRowCount(counter + 1)
                item1 = QtWidgets.QTableWidgetItem(field)
                item1.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
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

        if layer_type == "nodes":
            table = self.table_available_node_field
            final_table = self.table_node_fields
            # TODO : Change for the method .currentlayer()
            # Repeat the change throughout
            self.node_layer = get_vector_layer_by_name(self.node_layers_list.currentText())
            standard_fields = self.standard_fields_nodes
            unavailable_fields = Network.protected_fields + computed_node_fields
            layer = self.node_layer

        if layer_type == "links":
            table = self.table_available_link_fields
            final_table = self.table_link_fields
            self.link_layer = get_vector_layer_by_name(self.link_layers_list.currentText())
            standard_fields = self.standard_fields_links
            unavailable_fields = Network.protected_fields + computed_link_fields
            layer = self.link_layer

        if layer:
            layer_fields = [f for f in layer.fields() if f.name().lower() not in unavailable_fields]

        return layer_fields, table, final_table, standard_fields

    def changed_layer(self, layer_type):
        try:
            layer_fields, table, final_table, standard_fields = self.__find_layer_changed(layer_type)
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
                    item1.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    table.setItem(counter, 0, item1)
                    counter += 1
                self.counter[layer_type] = counter

            final_table.clearContents()
            final_table.setRowCount(0)

            counter = 0
            if layer_type == "links":
                from_layer, can_initialize = self.from_layer_links, initializable_link_fields
            else:
                from_layer, can_initialize = self.from_layer_nodes, []

            for rf in standard_fields:
                final_table.setRowCount(counter + 1)

                item1 = QtWidgets.QTableWidgetItem(rf)
                item1.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                final_table.setItem(counter, 0, item1)

                # The fields AequilibraE requires come from the layer and cannot be switched off, unless we
                # are able to initialize them ourselves. All the other ones start out initialized
                chb1 = QtWidgets.QCheckBox()
                chb1.setChecked(rf not in from_layer)
                chb1.setEnabled(rf not in from_layer or rf in can_initialize)
                chb1.stateChanged.connect(partial(self.set_field_to_default, layer_type))
                final_table.setCellWidget(counter, 1, self.centers_item(chb1))

                if rf in from_layer and layer_fields is not None:
                    cbb = QtWidgets.QComboBox()
                    for field in layer_fields:
                        cbb.addItem(field.name())
                    final_table.setCellWidget(counter, 2, self.centers_item(cbb))
                counter += 1
        except Exception as e:
            self.logger.error(e.args)

    def centers_item(self, item):
        cell_widget = QtWidgets.QWidget()
        lay_out = QtWidgets.QHBoxLayout(cell_widget)
        lay_out.addWidget(item)
        lay_out.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay_out.setContentsMargins(0, 0, 0, 0)
        cell_widget.setLayout(lay_out)
        return cell_widget

    def set_field_to_default(self, layer_type):
        layer_fields, table, final_table, standard_fields = self.__find_layer_changed(layer_type)

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
            self.qgis_project.iface_error_message(msg)
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
                return False, self.tr("Link Layer has NO defined CRS")

        if self.node_layer:
            if len(self.node_layer.crs().authid()) == 0:
                return False, self.tr("Node Layer has NO defined CRS")

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
        self.worker_thread.signal.connect(self.signal_handler)
        self.worker_thread.start()
        self.exec()

    def signal_handler(self, val):
        if val[0] == "start":
            self.progress_bridge.progress_started.emit(val[1], val[2])
        elif val[0] == "update":
            self.progress_bridge.progress_updated.emit(val[1])
        elif val[0] == "finished":
            self.progress_bridge.finished.emit()
            from qaequilibrae.modules.menu_actions.load_project_action import show_project_in_panel

            self.qgis_project.project = self.worker_thread.project
            show_project_in_panel(self.qgis_project, self.worker_thread.proj_folder)

            if self.worker_thread.report:
                dlg2 = ReportDialog(self.iface, self.worker_thread.report)
                dlg2.show()
                dlg2.exec()
            self.exit_procedure()

"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Creating the graph from geographic layer
 Purpose:    GUI for creating the graph

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    2018-12-27
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
from functools import partial
from qgis.core import *
import qgis
from qgis.PyQt.QtCore import *
from qgis.PyQt import QtWidgets, uic

from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *
from ..common_tools import GetOutputFileName, ReportDialog
from qgis.PyQt.QtWidgets import QComboBox, QTableWidgetItem, QCheckBox, QHBoxLayout, QRadioButton, QWidget
from .create_graph_procedure import GraphCreation
from .graph_centroids_dialog import GraphCentroids

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_Create_Graph.ui"))


class GraphCreationDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self)
        self.validtypes = integer_types + float_types
        self.iface = iface
        self.setupUi(self)
        self.layer = None
        self.centroids = None
        self.block_through_centroids = False
        self.selected_only = False
        self.fields_to_add = None
        self.cost_field = None
        self.link_id = None
        self.direction_field = None
        self.num_zones = -1
        self.error = None

        self.progressbar0.setVisible(False)
        self.progress_label0.setVisible(False)
        self.fields = 0
        self.fields_lst.setColumnWidth(0, 180)
        self.fields_lst.setColumnWidth(1, 180)
        self.fields_lst.setColumnWidth(2, 40)
        self.fields_lst.setColumnWidth(3, 60)

        # FIRST, we connect slot signals
        self.links_are_bi_directional.stateChanged.connect(self.bi_directional)
        self.chk_dual_fields.stateChanged.connect(self.dual_fields)

        # For changing the network layer
        self.network_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)

        # Calls the advanced features
        self.but_advanced.clicked.connect(self.call_advanced_features)

        # Create graph
        self.but_create_graph.clicked.connect(self.run_graph_creation)
        #
        self.select_result.clicked.connect(
            partial(self.browse_outfile, "Result file", self.graph_file, "Aequilibrae Graph(*.aeg)")
        )

        # THIRD, we load layers in the canvas to the combo-boxes
        self.network_layer.setFilters(QgsMapLayerProxyModel.LineLayer)

        # loads default path from parameters
        self.path = standard_path()
        self.dual_fields()
        self.bi_directional()
        self.load_fields_to_combo_boxes()
        self.check_if_ready()

    def bi_directional(self):
        if self.links_are_bi_directional.isChecked():
            self.chk_dual_fields.setVisible(True)
            self.dir_label.setVisible(True)
            self.cmb_direction_field.setVisible(True)
            self.fields_lst.setColumnWidth(1, 180)
            self.fields_lst.horizontalHeaderItem(0).setText("AB field")
            self.fields_lst.setGeometry(QRect(10, 130, 511, 261))
        else:
            self.chk_dual_fields.setVisible(True)
            self.dir_label.setVisible(False)
            self.cmb_direction_field.setVisible(False)
            self.fields_lst.setColumnWidth(1, 0)
            self.fields_lst.horizontalHeaderItem(0).setText("Link field")
            self.fields_lst.setGeometry(QRect(10, 130, 331, 261))
            self.chk_dual_fields.setCheckState(False)
        self.list_all_fields()

    def dual_fields(self):
        if self.chk_dual_fields.isChecked():
            self.fields_lst.setColumnWidth(1, 0)
            self.fields_lst.horizontalHeaderItem(0).setText("Fields *")
            self.fields_lst.setGeometry(QRect(10, 130, 331, 261))
        else:
            self.fields_lst.setColumnWidth(1, 180)
            self.fields_lst.horizontalHeaderItem(0).setText("AB field")
            self.fields_lst.setGeometry(QRect(10, 130, 511, 261))

        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.fields_lst.setSizePolicy(policy)
        self.list_all_fields()

    def set_initial_value_if_available(self, all_fields):
        def find_in_sequence(values, my_list):
            for val in values:
                for i in my_list:
                    if val in i:
                        return i
            return False

        link_id = find_in_sequence(["link_id", "link id", "lnk_id", "lnkid", "linkid", "link"], all_fields)
        if link_id:
            index = self.cmb_link_id.findText(link_id, Qt.MatchFixedString)
            if index >= 0:
                self.cmb_link_id.setCurrentIndex(index)

        direction = find_in_sequence(["direction", "dirn", "direc", "direct", "dir"], all_fields)
        if direction:
            index = self.cmb_direction_field.findText(direction, Qt.MatchFixedString)
            if index >= 0:
                self.cmb_direction_field.setCurrentIndex(index)

    # GENERIC to be applied to MORE THAN ONE form
    def load_fields_to_combo_boxes(self):
        i_types = [self.cmb_direction_field, self.cmb_link_id]

        for combo in i_types:
            combo.clear()

        all_fields = []
        if self.network_layer.currentIndex() >= 0:
            self.layer = get_vector_layer_by_name(self.network_layer.currentText())
            for field in self.layer.dataProvider().fields().toList():
                if field.name() not in reserved_fields:
                    if field.type() in integer_types:
                        for combo in i_types:
                            combo.addItem(field.name())
                            all_fields.append(field.name().lower())
        self.list_all_fields()
        self.set_initial_value_if_available(all_fields)

    def list_all_fields(self):
        self.fields_lst.setRowCount(0)
        self.fields = 0

        def add_new_field_to_list(text, sec_field):
            self.fields_lst.setRowCount(self.fields + 1)
            self.fields_lst.setItem(self.fields, 0, QTableWidgetItem(text))

            def centralized_widget(widget):
                my_widget = QWidget()
                # chk_bx.setCheckState(Qt.Checked) # If we wanted them all checked by default
                lay_out = QHBoxLayout(my_widget)
                lay_out.addWidget(widget)
                lay_out.setAlignment(Qt.AlignCenter)
                lay_out.setContentsMargins(0, 0, 0, 0)
                my_widget.setLayout(lay_out)
                return my_widget

            chk = centralized_widget(QCheckBox())
            q = QRadioButton()
            q.toggled.connect(self.handleItemClicked)
            chk2 = centralized_widget(q)

            self.fields_lst.setCellWidget(self.fields, 2, chk)
            self.fields_lst.setCellWidget(self.fields, 3, chk2)

            if sec_field is not None:
                cmb_bx = centralized_widget(sec_field)
                self.fields_lst.setCellWidget(self.fields, 1, cmb_bx)

            self.fields += 1

        if self.network_layer.currentIndex() >= 0:

            layer = get_vector_layer_by_name(self.network_layer.currentText())
            all_fields = layer.dataProvider().fields().toList()
            fields = []
            for field in all_fields:
                if field.type() in integer_types + float_types:
                    fields.append(field.name())
            fields = [x.lower() for x in fields]
            for f in reserved_fields:
                if f in fields:
                    fields.pop(f)

            if self.chk_dual_fields.isChecked():
                for field in fields:
                    if "_ab" in field:
                        if field.replace("_ab", "_ba") in fields:
                            fields.remove(field.replace("_ab", "_ba"))
                            field = field.replace("_ab", "_*")
                            add_new_field_to_list(field, None)
                    elif "_ba" in field:
                        if field.replace("_ba", "_ab") in fields:
                            fields.remove(field.replace("_ba", "_ab"))
                            field = field.replace("_ba", "_*")
                            add_new_field_to_list(field, None)
                    else:
                        add_new_field_to_list(field, None)
            else:
                for field in fields:
                    cmb_bx = QComboBox()
                    for f in fields:
                        cmb_bx.addItem(f)
                    cmb_bx.setCurrentIndex(cmb_bx.findText(field, Qt.MatchFixedString))
                    add_new_field_to_list(field, cmb_bx)
        self.check_if_ready()

    def handleItemClicked(self):
        box = self.sender()
        parent = box.parent()

        for i in range(self.fields):
            if self.fields_lst.cellWidget(i, 3) is parent:
                row = i
                break

        for i in range(self.fields):
            if i != row:
                for qradio in self.fields_lst.cellWidget(i, 3).findChildren(QRadioButton):
                    qradio.blockSignals(True)
                    qradio.setChecked(False)
                    qradio.blockSignals(False)
            else:
                for chkb in self.fields_lst.cellWidget(i, 2).findChildren(QCheckBox):
                    chkb.setChecked(True)

        for qradio in self.fields_lst.cellWidget(row, 3).findChildren(QRadioButton):
            qradio.blockSignals(True)
            qradio.setChecked(True)
            qradio.blockSignals(False)
        self.check_if_ready()

    def call_advanced_features(self):
        dlg2 = GraphCentroids(self.iface)
        dlg2.show()
        dlg2.exec_()
        self.centroids = dlg2.centroids
        self.block_through_centroids = dlg2.block_through_centroids
        self.num_zones = dlg2.num_zones
        self.check_if_ready()

    def run_thread(self):

        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressText.connect(self.progress_text_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.finished_threaded_procedure.connect(self.finished_threaded_procedure)

        self.worker_thread.start()
        self.exec_()

    # VAL and VALUE have the following structure: (bar/text ID, value)
    def progress_range_from_thread(self, val):
        self.progressbar0.setRange(0, val)

    def progress_value_from_thread(self, val):
        self.progressbar0.setValue(val)

    def progress_text_from_thread(self, val):
        self.progress_label0.setText(val)

    def finished_threaded_procedure(self, param):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage(
                "Input data not provided correctly", self.worker_thread.error, level=1
            )
        else:
            self.error = None
            try:
                self.worker_thread.graph.set_graph(
                    cost_field=self.cost_field, block_centroid_flows=self.block_through_centroids
                )
            except Exception as e:
                self.error = e
                self.output.append(self.error)
            self.worker_thread.graph.save_to_disk(self.output)
            qgis.utils.iface.messageBar().pushMessage("Finished. ", "Graph saved successfully", level=3)

        self.exit_procedure()

        if self.worker_thread.report:
            if self.error is not None:
                self.worker_thread.report.append("\n\n\n")
                self.worker_thread.report.append("##########   EXCEPTION:    ##########")
                self.worker_thread.report.append(error)

            dlg2 = ReportDialog(self.iface, self.worker_thread.report)
            dlg2.show()
            dlg2.exec_()

    def browse_outfile(self, dialogbox_name, outbox, file_types):
        new_name, file_type = GetOutputFileName(self, "Graph File", ["Aequilibrae Graph(*.aeg)"], ".aeg", self.path)
        if new_name is not None:
            outbox.setText(new_name)
            self.check_if_ready()

    def run_graph_creation(self):  # CREATING GRAPH
        self.check_if_ready()

        if self.error is None:
            self.fields_to_add = {}
            for i in range(self.fields):
                for chkbox in self.fields_lst.cellWidget(i, 2).findChildren(QCheckBox):
                    break
                if chkbox.isChecked():
                    field_name = self.fields_lst.item(i, 0).text()
                    if field_name[-1] == "*":
                        field_name = field_name[0:-1]
                        ab_field = field_name + "AB"
                        ba_field = field_name + "BA"
                        if field_name[-1] == "_" and len(field_name) > 1:
                            field_name = field_name[0:-1]
                        self.fields_to_add[field_name] = (
                            self.layer.dataProvider().fieldNameIndex(ab_field),
                            self.layer.dataProvider().fieldNameIndex(ba_field),
                        )
                    else:
                        if self.chk_dual_fields.isChecked():
                            if self.links_are_bi_directional.isChecked():
                                self.fields_to_add[field_name] = (
                                    self.layer.dataProvider().fieldNameIndex(field_name),
                                    self.layer.dataProvider().fieldNameIndex(field_name),
                                )
                            else:
                                self.fields_to_add[field_name] = (
                                    self.layer.dataProvider().fieldNameIndex(field_name),
                                    -1,
                                )
                        else:
                            if self.links_are_bi_directional.isChecked():
                                for cmb2 in self.fields_lst.cellWidget(i, 1).findChildren(QComboBox):
                                    break
                                b_field = cmb2.currentText()
                                self.fields_to_add[field_name] = (
                                    self.layer.dataProvider().fieldNameIndex(field_name),
                                    self.layer.dataProvider().fieldNameIndex(b_field),
                                )
                            else:
                                self.fields_to_add[field_name] = (
                                    self.layer.dataProvider().fieldNameIndex(field_name),
                                    -1,
                                )

        if self.error == None:
            self.progressbar0.setVisible(True)
            self.progress_label0.setVisible(True)

            self.lbl_funding1.setVisible(False)
            self.lbl_funding2.setVisible(False)
            self.worker_thread = GraphCreation(
                qgis.utils.iface.mainWindow(),
                self.layer,
                self.link_id,
                self.direction_field,
                self.fields_to_add,
                self.selected_only,
                self.centroids,
            )
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", self.error, level=3)

    def check_if_ready(self):
        self.but_create_graph.setEnabled(False)
        ready = True
        self.error = None

        if self.centroids is None:
            ready = False

        self.layer = get_vector_layer_by_name(self.network_layer.currentText())
        if self.layer is None:
            self.error = "Link layer not selected"

        self.output = self.graph_file.text().encode("ascii", "ignore")
        if self.error is None and self.output == "":
            self.error = "No file name was provided for the graph"

        if self.error is None:
            self.link_id = self.layer.dataProvider().fieldNameIndex(self.cmb_link_id.currentText())
            if self.link_id < 0:
                self.error = "ID Field not provided\n"

        if self.error is None:
            # Indices for the fields with time
            self.direction_field = None
            if self.links_are_bi_directional.isChecked():
                self.direction_field = self.layer.dataProvider().fieldNameIndex(self.cmb_direction_field.currentText())
                if self.direction_field < 0:
                    self.error = "Direction field not selected\n"

        if self.error is None:
            a = self.layer.dataProvider().fieldNameIndex("A_NODE")
            b = self.layer.dataProvider().fieldNameIndex("B_NODE")
            text = ""
            if a < 0:
                text = "No A_NODE field\n"
            if b < 0:
                text = text + "No B_NODE field"
            if text != "":
                self.error = text + ". Please prepare network"

        if self.error is None:
            self.cost_field = None
            for i in range(self.fields):
                for chk in self.fields_lst.cellWidget(i, 3).findChildren(QRadioButton):
                    if chk.isChecked():
                        self.cost_field = self.fields_lst.item(i, 0).text()
                        for chkbox in self.fields_lst.cellWidget(i, 2).findChildren(QCheckBox):
                            if not chkbox.isChecked():
                                self.error = "Cost field needs to be added to the graph"
            if self.cost_field is None:
                self.error = "Cost field not selected"

            elif self.cost_field[-2:] == "_*":
                self.cost_field = self.cost_field[:-2]

        if self.error is not None:
            ready = False

        if ready:
            self.but_create_graph.setEnabled(True)

    def exit_procedure(self):
        self.close()

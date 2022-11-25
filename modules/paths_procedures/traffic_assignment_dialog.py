import importlib.util as iutil
import logging
import numpy as np
import os
import pandas as pd
import re
import sys
from PyQt5.QtCore import Qt
from aequilibrae.parameters import Parameters
from aequilibrae.paths import Graph, AssignmentResults, allOrNothing
from aequilibrae.paths.traffic_assignment import TrafficAssignment
from aequilibrae.paths.traffic_class import TrafficClass
from aequilibrae.paths.vdf import all_vdf_functions
from aequilibrae.project import Project
from tempfile import gettempdir

import qgis
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QTableWidgetItem, QLineEdit, QComboBox, QCheckBox, QPushButton, QAbstractItemView
from ..common_tools import PandasModel
from ..common_tools import ReportDialog
from ..common_tools import standard_path

sys.modules["qgsmaplayercombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_traffic_assignment.ui"))
logger = logging.getLogger("AequilibraEGUI")


class TrafficAssignmentDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.setupUi(self)
        self.skimming = False
        self.path = standard_path()
        self.output_path = None
        self.temp_path = None
        self.error = None
        self.report = None
        self.current_modes = []
        self.assignment = TrafficAssignment()
        self.traffic_classes = {}
        self.vdf_parameters = {}
        self.matrices = pd.DataFrame([])
        self.skims = {}
        self.matrix = None
        self.block_centroid_flows = None
        self.worker_thread = None
        self.all_modes = {}
        self.__populate_project_info()
        self.rgap = "Undefined"
        self.iter = 0
        self.miter = 1000

        # Signals for the matrix_procedures tab
        self.but_add_skim.clicked.connect(self.__add_skimming)
        self.but_add_class.clicked.connect(self.__create_traffic_class)
        self.cob_matrices.currentIndexChanged.connect(self.change_matrix_selected)
        self.cob_mode_for_class.currentIndexChanged.connect(self.change_class_name)
        self.chb_fixed_cost.toggled.connect(self.set_fixed_cost_use)

        self.do_assignment.clicked.connect(self.run)
        self.cancel_all.clicked.connect(self.exit_procedure)

        # Signals for the algorithm tab
        for q in [self.progressbar0, self.progressbar1, self.progress_label0, self.progress_label1]:
            q.setVisible(False)

        for algo in self.assignment.all_algorithms:
            self.cb_choose_algorithm.addItem(algo)
        self.cb_choose_algorithm.setCurrentIndex(len(self.assignment.all_algorithms) - 1)

        for vdf in all_vdf_functions:
            self.cob_vdf.addItem(vdf)

        self.cob_vdf.currentIndexChanged.connect(self.__change_vdf)

        parameters = Parameters().parameters["assignment"]["equilibrium"]
        self.rel_gap.setText(str(parameters["rgap"]))
        self.max_iter.setText(str(parameters["maximum_iterations"]))

        # Queries
        tables = [self.select_link_list, self.list_link_extraction]
        for table in tables:
            table.setColumnWidth(0, 280)
            table.setColumnWidth(1, 40)
            table.setColumnWidth(2, 150)
            table.setColumnWidth(3, 40)

        self.tbl_project_properties.setColumnWidth(0, 120)
        self.tbl_project_properties.setColumnWidth(1, 450)

        # Disabling resources not yet implemented
        self.do_select_link.setEnabled(False)
        self.but_build_query.setEnabled(False)
        self.select_link_list.setEnabled(False)
        self.do_extract_link_flows.setEnabled(False)
        self.but_build_query_extract.setEnabled(False)
        self.list_link_extraction.setEnabled(False)

        self.tbl_traffic_classes.setColumnWidth(0, 125)
        self.tbl_traffic_classes.setColumnWidth(1, 125)
        self.skim_list_table.setColumnWidth(0, 200)
        self.skim_list_table.setColumnWidth(1, 200)
        self.skim_list_table.setColumnWidth(2, 200)
        self.skim_list_table.setColumnWidth(3, 200)

        self.tbl_vdf_parameters.setColumnWidth(0, 75)
        self.tbl_vdf_parameters.setColumnWidth(1, 75)
        self.tbl_vdf_parameters.setColumnWidth(2, 140)

        self.__change_vdf()
        self.change_matrix_selected()
        self.change_class_name()
        self.set_fixed_cost_use()

    def set_fixed_cost_use(self):
        for item in [self.cob_fixed_cost, self.lbl_vot, self.vot_setter]:
            item.setEnabled(self.chb_fixed_cost.isChecked())

        if self.chb_fixed_cost.isChecked():
            dt = self.project.conn.execute("pragma table_info(modes)").fetchall()
            if "vot" in [x[1] for x in dt]:
                sql = "select vot from modes where mode_id=?"
                v = self.project.conn.execute(sql, [self.all_modes[self.cob_mode_for_class.currentText()]]).fetchone()
                self.vot_setter.setValue(v[0])

    def change_class_name(self):
        nm = self.cob_mode_for_class.currentText()
        self.ln_class_name.setText(nm[:-4])
        self.set_fixed_cost_use()

        dt = self.project.conn.execute("pragma table_info(modes)").fetchall()
        if "pce" in [x[1] for x in dt]:
            sql = "select pce from modes where mode_id=?"
            v = self.project.conn.execute(sql, [self.all_modes[self.cob_mode_for_class.currentText()]]).fetchone()[0]
            if v is not None:
                self.pce_setter.setValue(v)

    def change_matrix_selected(self):
        mat_name = self.cob_matrices.currentText()
        self.but_add_class.setEnabled(False)
        if not mat_name:
            return

        if " (OMX not available)" in mat_name or " (file missing)" in mat_name:
            df = pd.DataFrame([])
        else:
            print(mat_name)
            matrix = self.project.matrices.get_matrix(mat_name)
            cores = matrix.names

            totals = [f"{np.nansum(matrix.get_matrix(x)):,.1f}" for x in cores]
            df = pd.DataFrame({"matrix_core": cores, "total": totals})
            self.but_add_class.setEnabled(True)
        matrices_model = PandasModel(df)
        self.tbl_core_list.setModel(matrices_model)
        self.tbl_core_list.setSelectionBehavior(QAbstractItemView.SelectRows)

    def __populate_project_info(self):
        table = self.tbl_project_properties
        table.setRowCount(2)

        # i.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        table.setItem(0, 0, QTableWidgetItem("Project path"))
        table.setItem(0, 1, QTableWidgetItem(self.project.path_to_file))

        curr = self.project.network.conn.cursor()
        curr.execute("""select mode_name, mode_id from modes""")

        modes = []
        for x in curr.fetchall():
            modes.append(f"{x[0]} ({x[1]})")
            self.all_modes[f"{x[0]} ({x[1]})"] = x[1]
            self.skims[x[1]] = []

        table.setItem(1, 0, QTableWidgetItem("Modes"))
        table.setItem(1, 1, QTableWidgetItem(", ".join(modes)))

        self.cob_mode_for_class.clear()
        for m in modes:
            self.cob_mode_for_class.addItem(m)

        # self.project.network.build_graphs()

        flds = self.project.network.skimmable_fields()
        for cob in [self.cob_skims_available, self.cob_capacity, self.cob_ffttime, self.cob_fixed_cost]:
            cob.clear()
            cob.addItems(flds)

        self.matrices = self.project.matrices.list()
        for idx, rec in self.matrices.iterrows():
            if not self.project.matrices.check_exists(rec["name"]):
                self.matrices.loc[idx, "name"] += " (file missing)"

        filter = self.matrices.file_name.str.contains(".omx", flags=re.IGNORECASE, regex=True)
        self.matrices.loc[filter, "name"] += " (OMX not available)"
        self.cob_matrices.clear()
        self.cob_matrices.addItems(self.matrices["name"].tolist())

    def __edit_skimming_modes(self):
        self.cob_skim_class.clear()
        for class_name in set(self.traffic_classes.keys()):
            self.cob_skim_class.addItem(class_name)

    def __change_vdf(self):
        table = self.tbl_vdf_parameters
        table.clearContents()
        if self.cob_vdf.currentText().lower() in ["bpr", "bpr2", "inrets", "conical"]:
            parameters = ["alpha", "beta"]
        else:
            return

        self.tbl_vdf_parameters.setRowCount(len(parameters))
        for i, par in enumerate(parameters):
            core_item = QTableWidgetItem(par)
            core_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(i, 0, core_item)

            val_item = QLineEdit()
            table.setCellWidget(i, 1, val_item)

            val_fld = QComboBox()
            for x in self.project.network.skimmable_fields():
                val_fld.addItem(x)
            table.setCellWidget(i, 2, val_fld)

    def __create_traffic_class(self):
        mat_name = self.cob_matrices.currentText()
        if not mat_name:
            return

        class_name = self.ln_class_name.text()
        if class_name in self.traffic_classes:
            qgis.utils.iface.messageBar().pushMessage("Class name already used", "", level=2)

        self.but_add_skim.setEnabled(True)

        matrix = self.project.matrices.get_matrix(mat_name)

        sel = self.tbl_core_list.selectionModel().selectedRows()
        if not sel:
            return
        rows = [s.row() for s in sel if s.column() == 0]
        user_classes = [matrix.names[i] for i in rows]
        matrix.computational_view(user_classes)

        mode = self.cob_mode_for_class.currentText()
        mode_id = self.all_modes[mode]
        if mode_id not in self.project.network.graphs:
            self.project.network.build_graphs(modes=[mode_id])

        graph = self.project.network.graphs[mode_id]

        if self.chb_chosen_links.isChecked():
            graph = self.project.network.graphs.pop(mode_id)
            idx = self.link_layer.dataProvider().fieldNameIndex("link_id")
            remove = [feat.attributes()[idx] for feat in self.link_layer.selectedFeatures()]
            graph.exclude_links(remove)

        graph.set_blocked_centroid_flows(self.chb_check_centroids.isChecked())
        assigclass = TrafficClass(class_name, graph, matrix)
        pce = self.pce_setter.value()
        assigclass.set_pce(pce)

        fcost = ""
        if self.chb_fixed_cost.isChecked():
            vot = self.vot_setter.value()
            assigclass.set_vot(vot)
            assigclass.set_fixed_cost(self.cob_fixed_cost.currentText())
            fcost = f"{vot:,.5f}*{self.cob_fixed_cost.currentText()}"

        self.traffic_classes[class_name] = assigclass

        num_classes = len([x for x in self.traffic_classes.values() if x is not None])

        table = self.tbl_traffic_classes
        table.setRowCount(num_classes)
        self.project.matrices.reload()

        idx = num_classes - 1
        for i, txt in enumerate([class_name, mode, str(len(user_classes)), fcost, str(round(pce, 4))]):
            item = QTableWidgetItem(txt)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(idx, i, item)

        but = QPushButton()
        but.setText("Remove")
        but.clicked.connect(self.__remove_class)
        but.setEnabled(False)
        table.setCellWidget(idx, 5, but)

        self.current_modes.append(mode)
        self.__edit_skimming_modes()
        self.skims[class_name] = []

    def __add_skimming(self):

        field = self.cob_skims_available.currentText()
        traffic_class = self.traffic_classes[self.cob_skim_class.currentText()]
        name = traffic_class.__id__
        if field in self.skims[name]:
            return

        table = self.skim_list_table
        idx = table.rowCount()
        table.setRowCount(idx + 1)

        for i, val in enumerate([self.cob_skim_class.currentText(), field]):
            item = QTableWidgetItem(val)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(idx, i, item)

        last_chb = QCheckBox()
        last_chb.setChecked(True)
        table.setCellWidget(idx, 2, last_chb)

        blended_chb = QCheckBox()
        blended_chb.setChecked(True)
        table.setCellWidget(idx, 3, blended_chb)

        self.skims[name].append(field)
        self.skimming = True

    def __remove_class(self):
        self.__edit_skimming_modes()

    def run_thread(self):
        self.worker_thread.assignment.connect(self.signal_handler)
        if self.cb_choose_algorithm.currentText() != "all-or-nothing":
            self.worker_thread.equilibration.connect(self.equilibration_signal_handler)
        self.worker_thread.start()
        self.exec_()

    def job_finished_from_thread(self):
        # self.report = self.worker_thread.report
        self.produce_all_outputs()

        self.exit_procedure()

    def run(self):
        if not self.check_data():
            qgis.utils.iface.messageBar().pushMessage("Input error", self.error, level=3)

        algorithm = self.cb_choose_algorithm.currentText()
        self.miter = int(self.max_iter.text())
        if algorithm != "all-or-nothing":
            for q in [self.progressbar1, self.progress_label1]:
                q.setVisible(True)
            self.progressbar1.setRange(0, self.miter)

        for q in [self.progressbar0, self.progress_label0]:
            q.setVisible(True)
            self.progressbar0.setRange(0, self.project.network.count_centroids())

        self.assignment.set_classes(list(self.traffic_classes.values()))
        self.assignment.set_vdf(self.cob_vdf.currentText())
        self.assignment.set_vdf_parameters(self.vdf_parameters)
        self.assignment.set_capacity_field(self.cob_capacity.currentText())
        self.assignment.set_time_field(self.cob_ffttime.currentText())
        self.assignment.set_algorithm(self.cb_choose_algorithm.currentText())
        self.assignment.max_iter = self.miter
        self.assignment.rgap_target = float(self.rel_gap.text())
        self.worker_thread = self.assignment.assignment
        self.run_thread()

    def check_data(self):
        self.error = None

        num_classes = len(self.traffic_classes.values())
        if not num_classes:
            self.error = "No traffic classes to assign"
            return False

        self.scenario_name = self.output_scenario_name.text()
        if not self.scenario_name:
            self.error = "Missing scenario name"
            return False

        if not self.scenario_name:
            self.error = "Missing scenario name"
            return False

        sql = "Select count(*) from results where table_name=?"
        if sum(self.project.conn.execute(sql, [self.scenario_name]).fetchone()):
            self.error = "Result table name already exists. Choose a new name"
            return False

        self.temp_path = gettempdir()
        tries_setup = self.set_assignment()
        return tries_setup

    def signal_handler(self, val):
        if val[0] == "zones finalized":
            self.progressbar0.setValue(val[1])
        elif val[0] == "text AoN":
            self.progress_label0.setText(val[1])
        elif val[0] == "finished_threaded_procedure":
            self.progressbar0.setValue(0)
            if self.cb_choose_algorithm.currentText() == "all-or-nothing":
                self.job_finished_from_thread()

    def equilibration_signal_handler(self, val):
        if val[0] == "iterations":
            self.progressbar1.setValue(val[1])
            self.iter = val[1]
        elif val[0] == "rgap":
            self.rgap = val[1]
        elif val[0] == "finished_threaded_procedure":
            self.job_finished_from_thread()
        self.progress_label1.setText(f"{self.iter}/{self.miter} - Rel. Gap {self.rgap:.2E}")

    # Save link flows to disk
    def produce_all_outputs(self):
        self.assignment.save_results(self.scenario_name)
        if self.skimming:
            self.assignment.save_skims(self.scenario_name, which_ones="all", format="omx")

    # def click_button_inside_the_list(self, purpose):
    #     if purpose == "select link":
    #         table = self.select_link_list
    #     else:
    #         table = self.list_link_extraction
    #
    #     button = self.sender()
    #     index = self.select_link_list.indexAt(button.pos())
    #     row = index.row()
    #     table.removeRow(row)
    #
    #     if purpose == "select link":
    #         self.tot_crit_link_queries -= 1
    #     elif purpose == "Link flow extraction":
    #         self.tot_link_flow_extract -= 1

    def set_assignment(self):
        for k, cls in self.traffic_classes.items():
            if self.skims[k]:
                dt = cls.graph.block_centroid_flows
                logger.debug(f"Set skims {self.skims[k]} for {k}")
                cls.graph.set_graph(self.cob_ffttime.currentText())
                cls.graph.set_skimming(self.skims[k])
                cls.graph.set_blocked_centroid_flows(dt)

        table = self.tbl_vdf_parameters
        for i in range(table.rowCount()):
            k = table.item(i, 0).text()
            val = table.cellWidget(i, 1).text()
            if len(val) == 0:
                val = table.cellWidget(i, 2).currentText()
            else:
                try:
                    val = float(val)
                except Exception as e:
                    self.error = "VDF parameter is not numeric"
                    logger.error(f"Tried to set a VDF parameter not numeric. {e.args}")
                    return False
            self.vdf_parameters[k] = val

        return True

    def exit_procedure(self):
        self.close()
        if self.report:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()

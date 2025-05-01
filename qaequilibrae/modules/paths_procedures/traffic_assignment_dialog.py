import logging
import os
import sys
from tempfile import gettempdir

import numpy as np
import pandas as pd
import qgis
from PyQt5.QtCore import Qt
from aequilibrae.parameters import Parameters
from aequilibrae.paths.traffic_assignment import TrafficAssignment
from aequilibrae.paths.traffic_class import TrafficClass
from aequilibrae.paths.vdf import all_vdf_functions
from aequilibrae.project.database_connection import database_connection
from aequilibrae.utils.db_utils import commit_and_close
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QTableWidgetItem, QLineEdit, QComboBox, QCheckBox, QPushButton, QAbstractItemView

from qaequilibrae.modules.common_tools import PandasModel, ReportDialog, standard_path

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
        self.select_links = {}
        self.__current_links = []
        self.__project_links = self.project.network.links.data.link_id

        # Signals for the matrix_procedures tab
        self.but_add_skim.clicked.connect(self._add_skimming)
        self.but_add_class.clicked.connect(self._create_traffic_class)
        self.cob_matrices.currentIndexChanged.connect(self.change_matrix_selected)
        self.cob_mode_for_class.currentIndexChanged.connect(self.change_class_name)
        self.chb_fixed_cost.toggled.connect(self.set_fixed_cost_use)
        self.do_select_link.toggled.connect(self.set_select_link_use)

        self.do_assignment.clicked.connect(self.run)
        self.cancel_all.clicked.connect(self.exit_procedure)

        # Signals for the algorithm tab
        for q in [self.progressbar, self.progress_label]:
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
            table.setColumnWidth(0, 240)
            table.setColumnWidth(1, 120)
            table.setColumnWidth(2, 150)
            table.setColumnWidth(3, 40)

        self.tbl_project_properties.setColumnWidth(0, 120)
        self.tbl_project_properties.setColumnWidth(1, 450)

        # We'll temporarily remove the tab instead of disabling its resources
        self.tabWidget.removeTab(4)

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
        self.set_select_link_use()

        # Set up select link analysis
        self.cob_direction.addItems(["AB", "Both", "BA"])
        self.but_add_query.clicked.connect(self.add_query)
        self.but_build_query.clicked.connect(self.build_query)
        self.select_link_list.cellDoubleClicked.connect(self.__remove_select_link_item)
        self.but_clean.clicked.connect(self.__clean_link_selection)

    def set_fixed_cost_use(self):
        for item in [self.cob_fixed_cost, self.lbl_vot, self.vot_setter]:
            item.setEnabled(self.chb_fixed_cost.isChecked())

        if self.chb_fixed_cost.isChecked():
            with self.project.db_connection as conn:
                dt = conn.execute("pragma table_info(modes)").fetchall()
                if "vot" in [x[1] for x in dt]:
                    sql = "select vot from modes where mode_id=?"
                    v = conn.execute(sql, [self.all_modes[self.cob_mode_for_class.currentText()]]).fetchone()
                    self.vot_setter.setValue(v[0])

    def change_class_name(self):
        nm = self.cob_mode_for_class.currentText()
        self.ln_class_name.setText(nm[:-4])
        self.set_fixed_cost_use()

        with self.project.db_connection as conn:
            dt = conn.execute("pragma table_info(modes)").fetchall()
            if "pce" in [x[1] for x in dt]:
                sql = "select pce from modes where mode_id=?"
                v = conn.execute(sql, [self.all_modes[self.cob_mode_for_class.currentText()]]).fetchone()[0]
                if v is not None:
                    self.pce_setter.setValue(v)

    def change_matrix_selected(self):
        mat_name = self.cob_matrices.currentText()
        self.but_add_class.setEnabled(False)
        if not mat_name:
            return

        if " (file missing)" in mat_name:
            df = pd.DataFrame([])
        else:
            matrix = self.project.matrices.get_matrix(mat_name)
            cores = matrix.names

            totals = [f"{np.nansum(matrix.get_matrix(x)):,.1f}" for x in cores]
            df = pd.DataFrame({"matrix_core": cores, "total": totals})
            self.but_add_class.setEnabled(True)
        matrices_model = PandasModel(df)
        self.tbl_core_list.setModel(matrices_model)
        self.tbl_core_list.setSelectionBehavior(QAbstractItemView.SelectRows)

    def __populate_project_info(self):
        path_to_file = str(self.project.path_to_file)

        table = self.tbl_project_properties
        table.setRowCount(2)

        table.setItem(0, 0, QTableWidgetItem("Project path"))
        table.setItem(0, 1, QTableWidgetItem(path_to_file))

        with commit_and_close(database_connection("network")) as conn:
            res = conn.execute("""select mode_name, mode_id from modes""")

            modes = []
            for x in res.fetchall():
                modes.append(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]
                self.skims[x[1]] = []

        table.setItem(1, 0, QTableWidgetItem("Modes"))
        table.setItem(1, 1, QTableWidgetItem(", ".join(modes)))

        self.cob_mode_for_class.clear()
        for m in modes:
            self.cob_mode_for_class.addItem(m)

        flds = self.project.network.skimmable_fields()
        for cob in [self.cob_skims_available, self.cob_capacity, self.cob_ffttime, self.cob_fixed_cost]:
            cob.clear()
            cob.addItems(flds)

        self.matrices = self.project.matrices.list()
        for idx, rec in self.matrices.iterrows():
            if not self.project.matrices.check_exists(rec["name"]):
                self.matrices.loc[idx, "name"] += " (file missing)"

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

    def _create_traffic_class(self):
        mat_name = self.cob_matrices.currentText()
        if not mat_name:
            raise AttributeError("Matrix not set")

        class_name = self.ln_class_name.text()
        if class_name in self.traffic_classes:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Class name already used"), "", level=2, duration=10)

        self.but_add_skim.setEnabled(True)

        matrix = self.project.matrices.get_matrix(mat_name)

        sel = self.tbl_core_list.selectionModel().selectedRows()
        if not sel:
            raise AttributeError("Matrix cores not chosen")
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
        but.setText(self.tr("Remove"))
        but.clicked.connect(self.__remove_class)
        but.setEnabled(False)
        table.setCellWidget(idx, 5, but)

        self.current_modes.append(mode)
        self.__edit_skimming_modes()
        self.skims[class_name] = []

    def _add_skimming(self):
        field = self.cob_skims_available.currentText()
        traffic_class = self.traffic_classes[self.cob_skim_class.currentText()]
        name = traffic_class._id
        if field in self.skims[name]:
            raise AttributeError("No skims set")

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

    def add_query(self):
        link_id = self.__validate_link_id()

        direction = self.cob_direction.currentText()

        if direction == "AB":
            self.__current_links.extend([(link_id, 1)])
        elif direction == "BA":
            self.__current_links.extend([(link_id, -1)])
        else:
            self.__current_links.extend([(link_id, 0)])

    def __validate_link_id(self):
        link_id = self.input_link_id.text()

        # Check if we have only numbers
        if not link_id.isdigit():
            self.error = self.tr("Wrong value for link ID")
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=5)
            return

        # Check if link_id exists
        link_id = int(link_id)
        if link_id not in self.__project_links:
            self.error = self.tr("Link ID doesn't exist in project")
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=2, duration=5)
            return

        return link_id

    def build_query(self):
        query_name = self.input_qry_name.text()

        if len(query_name) == 0 or not query_name:
            self.error = self.tr("Missing query name")
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=5)
            return

        if query_name in self.select_links:
            self.error = self.tr("Query name already used")
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=5)
            return

        if not self.__current_links:
            self.error = self.tr("Please set a link selection")
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=5)
            return

        self.select_links[query_name] = self.__current_links

        self.select_link_list.clearContents()
        self.select_link_list.setRowCount(len(self.select_links.keys()))

        for i, (name, links) in enumerate(self.select_links.items()):
            self.select_link_list.setItem(i, 0, QTableWidgetItem(str(links)))
            self.select_link_list.setItem(i, 1, QTableWidgetItem(str(name)))

        self.__current_links = []

    def set_select_link_use(self):
        for item in [self.select_link_list, self.select_link_config]:
            item.setEnabled(self.do_select_link.isChecked())

    def __remove_select_link_item(self, line):
        key = list(self.select_links.keys())[line]
        self.select_link_list.removeRow(line)

        self.select_links.pop(key)

    def __clean_link_selection(self):
        self.input_qry_name.clear()
        self.input_link_id.clear()
        self.cob_direction.setCurrentIndex(0)
        self.__current_links = []

    def __remove_class(self):
        self.__edit_skimming_modes()

    def run_thread(self):
        self.worker_thread.signal.connect(self.signal_handler)
        self.worker_thread.start()
        self.exec_()

    def job_finished_from_thread(self):
        self.produce_all_outputs()

        self.exit_procedure()

    def run(self):
        if not self.check_data():
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=5)
            return

        self.miter = int(self.max_iter.text())
        for q in [self.progressbar, self.progress_label]:
            q.setVisible(True)
        self.progressbar.setRange(0, self.project.network.count_centroids())

        self.assignment.set_classes(list(self.traffic_classes.values()))
        self.assignment.set_vdf(self.cob_vdf.currentText())
        self.assignment.set_vdf_parameters(self.vdf_parameters)
        self.assignment.set_capacity_field(self.cob_capacity.currentText())
        self.assignment.set_time_field(self.cob_ffttime.currentText())
        self.assignment.max_iter = self.miter
        self.assignment.rgap_target = float(self.rel_gap.text())
        self.assignment.set_algorithm(self.cb_choose_algorithm.currentText())
        self.assignment.log_specification()

        if self.do_select_link.isChecked():
            for traffic_class in self.traffic_classes.values():
                traffic_class.set_select_links(self.select_links)

        self.worker_thread = self.assignment.assignment
        self.run_thread()

    def check_data(self):
        self.error = None

        num_classes = len(self.traffic_classes.values())
        if not num_classes:
            self.error = self.tr("No traffic classes to assign")
            return False

        self.scenario_name = self.output_scenario_name.text()
        if not self.scenario_name:
            self.error = self.tr("Missing scenario name")
            return False

        sql = "Select count(*) from results where table_name=?"
        with self.project.db_connection as conn:
            if sum(conn.execute(sql, [self.scenario_name]).fetchone()):
                self.error = self.tr("Result table name already exists. Choose a new name")
                return False

        if self.do_select_link.isChecked():
            self.output_name = self.sl_mat_name.text()
            if len(self.output_name) == 0:
                self.error = self.tr("Missing select link matrix name.")
                return False

            if self.output_name in self.matrices:
                self.error = self.tr("Result matrix name already exists. Choose a new name.")
                return False

        self.temp_path = gettempdir()
        tries_setup = self.set_assignment()
        return tries_setup

    def signal_handler(self, val):
        if val[0] == "start":
            self.progressbar.setValue(0)
            self.progressbar.setMaximum(val[1])
            self.progress_label.setText(val[2])
        elif val[0] == "update":
            self.progressbar.setValue(val[1])
            self.progress_label.setText(val[2])
        elif val[0] == "finished":
            self.job_finished_from_thread()

    # Save link flows to disk
    def produce_all_outputs(self):
        if self.do_select_link.isChecked():
            if self.chb_save_matrix.isChecked():
                self.assignment.save_select_link_matrices(self.output_name)

            # These two lines are raising an sqlite3 error in pytest
            if self.chb_save_result.isChecked():
                self.assignment.save_select_link_flows(self.output_name)

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
                    self.error = self.tr("VDF parameter is not numeric")
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

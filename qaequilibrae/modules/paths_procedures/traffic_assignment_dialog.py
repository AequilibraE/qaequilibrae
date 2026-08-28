from collections import defaultdict
from tempfile import gettempdir
from os.path import dirname, join
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from aequilibrae.context import get_logger
from aequilibrae.parameters import Parameters
from aequilibrae.paths.traffic_assignment import TrafficAssignment
from aequilibrae.paths.traffic_class import TrafficClass
from aequilibrae.paths.vdf import all_vdf_functions
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QPalette
from qgis.PyQt.QtWidgets import QTableWidgetItem, QLineEdit, QComboBox, QCheckBox, QPushButton, QAbstractItemView

from .create_py_strings import create_strings
from qaequilibrae.modules.common_tools import PandasModel, ReportDialog, standard_path, GetOutputFileName, BaseDialog

logger = get_logger()

# What each volume-delay function actually takes, mirroring the parameter bounds AequilibraE
# checks in TrafficAssignment.set_vdf_parameters. Offering the wrong set here either leaves the
# user with nothing to fill in (Akcelik) or with a field the function never reads (INRETS).
# How far the second band sits from the first, in absolute HSL lightness. Two figures because
# a step that reads clearly against white is nearly invisible against a dark background
BAND_STEP_FROM_LIGHT = 15
BAND_STEP_FROM_DARK = 18

VDF_PARAMETERS = {
    "bpr": ["alpha", "beta"],
    "bpr2": ["alpha", "beta"],
    "conical": ["alpha", "beta"],
    "inrets": ["alpha"],
    "akcelik": ["alpha", "tau", "length"],
}


class TrafficAssignmentDialog(BaseDialog):
    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_traffic_assignment.ui"), qgis_project=qgis_project)

    def _base_ui_setup(self):
        self.project = self.qgis_project.project
        self.skimming = False
        self.path = standard_path()
        self.output_path = None
        self.temp_path = None
        self.error = None
        self.report = None
        self.current_modes = []
        self.assignment = TrafficAssignment()
        self.traffic_classes = {}
        self.class_cores = {}
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
        self.__rebuilt_modes = set()
        self.__current_links = []
        self.__project_links = self.project.network.links.data.link_id
        self.link_layer = self.qgis_project.layers["links"][0]
        self._from_yaml = False

        # Signals for the project tab
        self.but_load_yaml.clicked.connect(self._load_configs)

        # Signals for the matrix_procedures tab
        self.but_add_skim.clicked.connect(self._add_skimming)
        self.skim_list_table.cellDoubleClicked.connect(self._remove_skimming)
        self.cob_skim_class.currentIndexChanged.connect(self.refresh_available_skims)
        self.but_add_class.clicked.connect(self._create_traffic_class)
        self.cob_matrices.currentIndexChanged.connect(self.change_matrix_selected)
        self.cob_mode_for_class.currentIndexChanged.connect(self.change_class_name)
        self.chb_fixed_cost.toggled.connect(self.set_fixed_cost_use)
        self.do_select_link.toggled.connect(self.set_select_link_use)

        self.but_save_yaml.clicked.connect(self.export_yaml)
        self.but_save_python.clicked.connect(self.export_python)

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

    def _browse_yaml_path(self):
        file_path, _ = GetOutputFileName(QtWidgets.QDialog(), "Configuration file", ["YAML (*.yml)"], ".yml", self.path)
        return file_path

    def _browse_python_path(self):
        path = str(self.project.project_base_path / "run")
        file_path, _ = GetOutputFileName(QtWidgets.QDialog(), "", ["Python (*.py)"], ".py", path)
        return file_path

    def __select_option(self, combo: QComboBox, value: str, description: str):
        """Selects `value` in `combo`, refusing a config that asks for an option that is not there."""
        idx = combo.findText(value, Qt.MatchFlag.MatchFixedString)
        if idx < 0:
            options = ", ".join(combo.itemText(i) for i in range(combo.count()))
            raise ValueError(f"'{value}' is not an available {description}. Options are: {options}")
        combo.setCurrentIndex(idx)

    def _load_configs(self):
        # Let's open the YAML config file
        file_path = self._browse_yaml_path()

        if file_path:
            with open(file_path, "r") as f:
                params = yaml.safe_load(f)

            self._from_yaml = True

            # Populate Traffic Classes tab
            for tc in params["traffic_classes"]:
                for key, value in tc.items():
                    self.__select_option(self.cob_matrices, value["matrix_name"], "matrix")
                    self.change_matrix_selected()
                    # From the combo rather than from the config, so that the cores listed below
                    # come from the same matrix `_create_traffic_class` is going to pick up
                    names = self.project.matrices.get_matrix(self.cob_matrices.currentText()).names
                    self.tbl_core_list.selectRow(names.index(value["matrix_core"]))
                    self.ln_class_name.setText(key)
                    self.pce_setter.setValue(value["pce"])
                    self.chb_check_centroids.setChecked(value["blocked_centroid_flows"])
                    # Cleared as much as set: `_create_traffic_class` reads this checkbox for every
                    # class, so leaving it on would hand the next class the previous one's fixed cost
                    self.chb_fixed_cost.setChecked("fixed_cost" in value)
                    if "fixed_cost" in value:
                        self.__select_option(self.cob_fixed_cost, value["fixed_cost"], "fixed cost field")
                        self.vot_setter.setValue(value["vot"])
                    self._create_traffic_class(value["network_mode"])

                    # Populate Skimming tab, through the same redraw the buttons go through
                    if "skims" in value:
                        traffic_class = self.traffic_classes[key]
                        choices = self.skim_choices()
                        for skim, config in value["skims"].items():
                            self.skims[traffic_class._id].append(skim)
                            choices[(key, skim)] = ("final" in config, "blended" in config)
                        self.redraw_skim_table(choices)
                        self.refresh_available_skims()

            # Populate Critical Analysis tab
            if "select_links" in params:
                self.do_select_link.setChecked(True)

                # We manually input `add_query` and `build_query`
                for qry, links in params["select_links"]["selection"].items():
                    self.__current_links.extend([tuple(link) for link in links])
                    self.build_query(qry)

                self.sl_mat_name.setText(params["select_links"]["output_name"])
                if "save_matrix" in params["select_links"]:
                    self.chb_save_matrix.setChecked(params["select_links"]["save_matrix"])
                if "save_result" in params["select_links"]:
                    self.chb_save_result.setChecked(params["select_links"]["save_result"])

            # Populate Assignment tab
            self.__select_option(self.cb_choose_algorithm, params["assignment"]["algorithm"], "algorithm")
            self.max_iter.setText(str(params["assignment"]["max_iter"]))
            self.rel_gap.setText(str(params["assignment"]["rgap"]))

            self.__select_option(self.cob_capacity, params["assignment"]["capacity_field"], "capacity field")
            self.__select_option(self.cob_ffttime, params["assignment"]["time_field"], "free-flow time field")

            # Ahead of the parameters below, because changing it rebuilds the parameters table.
            # `all_vdf_functions` fills the combo in lower case, so a config asking for "BPR2"
            # only ever lands because the match below ignores case
            self.__select_option(self.cob_vdf, params["assignment"]["vdf"], "volume-delay function")

            # Driven by the rows the function above just put in the table, so each function
            # picks up its own parameters and ignores any the config carries for another one
            table = self.tbl_vdf_parameters
            for i in range(table.rowCount()):
                name = table.item(i, 0).text()
                if name not in params["assignment"]:
                    continue
                value = params["assignment"][name]
                if isinstance(value, str):
                    self.__select_option(table.cellWidget(i, 2), value, f"field for the VDF {name}")
                else:
                    table.cellWidget(i, 1).setText(str(value))

            self.output_scenario_name.setText(params["assignment"]["result_name"])

    def export_yaml(self):
        file_path = self._browse_yaml_path()

        if file_path:
            self.check_data()

            data_dict = {"traffic_classes": [], "assignment": {}}

            # Add traffic class data
            for idx, (tc, info) in enumerate(self.traffic_classes.items()):
                data_dict["traffic_classes"].extend([{tc: {}}])
                dc = data_dict["traffic_classes"][idx][tc]

                pth = Path(info.matrix.file_path).name
                df = self.project.matrices.list()
                dc["matrix_name"] = df.loc[df["file_name"] == pth]["name"].values[0]
                dc["matrix_core"] = self.class_cores[tc][0]
                dc["network_mode"] = info.mode
                dc["pce"] = info.pce
                # Taken from the class rather than from the checkbox, which only reflects the class
                # currently being edited: keying off it would write the fixed cost for classes that
                # do not have one, or drop it from those that do
                if info.fixed_cost_field:
                    dc["fixed_cost"] = info.fixed_cost_field
                    dc["vot"] = info.vot
                dc["blocked_centroid_flows"] = info.graph.block_centroid_flows
                if self.skims[tc]:
                    if "skims" not in dc.keys():
                        dc["skims"] = {}
                    for i in range(self.skim_list_table.rowCount()):
                        if self.skim_list_table.item(i, 0).text() == tc:
                            field = self.skim_list_table.item(i, 1).text()
                            dc["skims"][field] = []
                            if self.skim_list_table.cellWidget(i, 2).isChecked():
                                dc["skims"][field].extend(["final"])
                            if self.skim_list_table.cellWidget(i, 3).isChecked():
                                dc["skims"][field].extend(["blended"])

            # Add assignment data
            data_dict["assignment"]["algorithm"] = self.cb_choose_algorithm.currentText()
            data_dict["assignment"]["max_iter"] = int(self.max_iter.text())
            data_dict["assignment"]["rgap"] = float(self.rel_gap.text())
            data_dict["assignment"]["capacity_field"] = self.cob_capacity.currentText()
            data_dict["assignment"]["time_field"] = self.cob_ffttime.currentText()
            data_dict["assignment"]["result_name"] = self.scenario_name

            data_dict["assignment"]["vdf"] = self.cob_vdf.currentText()
            # Written row by row rather than as a fixed alpha/beta pair, so that a function with
            # its own parameters - Akcelik's tau and length - survives the round trip
            table = self.tbl_vdf_parameters
            for i in range(table.rowCount()):
                name = table.item(i, 0).text()
                typed = table.cellWidget(i, 1).text()
                data_dict["assignment"][name] = float(typed) if typed else table.cellWidget(i, 2).currentText()

            # Add Select Link Analysis data
            if self.do_select_link.isChecked():
                data_dict["select_links"] = {"selection": {}}
                for qry, links in self.select_links.items():
                    data_dict["select_links"]["selection"][qry] = [list(lnk) for lnk in links]
                data_dict["select_links"]["output_name"] = self.sl_mat_name.text()
                data_dict["select_links"]["save_matrix"] = self.chb_save_matrix.isChecked()
                data_dict["select_links"]["save_result"] = self.chb_save_result.isChecked()

            with open(file_path, "w") as file:
                yaml.dump(data_dict, file, default_flow_style=False)

    def export_python(self):
        out_name = self._browse_python_path()

        if out_name:
            self.check_data()

            info_dict = {
                "classes": [],
                "assignment": [],
                "scenario_name": self.scenario_name,
                "skimming": self.skimming,
                "out_name": out_name,
                "project_path": self.project.project_base_path,
            }

            df = self.project.matrices.list()
            for tc, info in self.traffic_classes.items():
                pth = Path(info.matrix.file_path).name
                info_dict["classes"].extend(
                    [
                        [
                            info.graph.mode,
                            self.cob_ffttime.currentText(),
                            self.skims[tc] if self.skims[tc] else [],
                            info.graph.block_centroid_flows,
                            df.loc[df["file_name"] == pth]["name"].values[0],
                            self.class_cores[tc][0],
                            tc,
                        ]
                    ]
                )

            info_dict["assignment"].extend(
                [
                    self.cob_vdf.currentText(),
                    self.vdf_parameters,
                    self.cob_capacity.currentText(),
                    self.cob_ffttime.currentText(),
                    self.cb_choose_algorithm.currentText(),
                    self.miter,
                    float(self.rel_gap.text()),
                ]
            )

            if self.do_select_link.isChecked():
                info_dict["select_links"] = {
                    "select_links": [self.select_links],
                    "output_name": self.sl_mat_name.text(),
                    "save_matrix": self.chb_save_matrix.isChecked(),
                    "save_result": self.chb_save_result.isChecked(),
                }

            _ = create_strings(info_dict)

            p = Parameters()
            p.parameters["run"]["run_assignment"] = None
            p.write_back()

    def set_fixed_cost_use(self):
        for item in [self.cob_fixed_cost, self.lbl_vot, self.vot_setter]:
            item.setEnabled(self.chb_fixed_cost.isChecked())

        if self.chb_fixed_cost.isChecked():
            with self.project.db_connection as conn:
                dt = conn.execute("pragma table_info(modes)").fetchall()
                if "vot" in [x[1] for x in dt]:
                    sql = "select vot from modes where mode_id=?"
                    v = conn.execute(sql, [self.all_modes[self.cob_mode_for_class.currentText()]]).fetchone()[0]
                    if v:
                        self.vot_setter.setValue(v)
                    else:
                        msg = self.tr("No VoT found for mode {} in project database. Please configure it.")
                        self.qgis_project.iface_warning_message(msg.format(self.cob_mode_for_class.currentText()))

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
        self.tbl_core_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    def __populate_project_info(self):
        path_to_file = str(self.project.path_to_file)

        table = self.tbl_project_properties
        table.setRowCount(2)

        table.setItem(0, 0, QTableWidgetItem("Project path"))
        table.setItem(0, 1, QTableWidgetItem(path_to_file))

        with self.project.db_connection as conn:
            res = conn.execute("""select mode_name, mode_id from modes""")

            modes = []
            for x in res.fetchall():
                modes.append(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        table.setItem(1, 0, QTableWidgetItem("Modes"))
        table.setItem(1, 1, QTableWidgetItem(", ".join(modes)))

        self.cob_mode_for_class.clear()
        for m in modes:
            self.cob_mode_for_class.addItem(m)

        self.skimmable_fields = self.project.network.skimmable_fields()
        for cob in [self.cob_skims_available, self.cob_capacity, self.cob_ffttime, self.cob_fixed_cost]:
            cob.clear()
            cob.addItems(self.skimmable_fields)

        self.matrices = self.project.matrices.list()
        for idx, rec in self.matrices.iterrows():
            if not self.project.matrices.check_exists(rec["name"]):
                self.matrices.loc[idx, "name"] += " (file missing)"

        self.cob_matrices.clear()
        self.cob_matrices.addItems(self.matrices["name"].tolist())

    def __edit_skimming_modes(self):
        self.cob_skim_class.clear()
        # Sorted rather than iterated over a set, which put the classes in an order that had
        # nothing to do with either their names or the order they were created in
        for class_name in sorted(self.traffic_classes):
            self.cob_skim_class.addItem(class_name)
        self.refresh_available_skims()

    def refresh_available_skims(self):
        """Offers only the fields not already being skimmed for the class on display"""
        taken = self.skims.get(self.cob_skim_class.currentText(), [])
        # Alphabetical, rather than the order the fields happen to sit in on the links table
        available = sorted(fld for fld in self.skimmable_fields if fld not in taken)

        # Held on to so that switching class, or removing a skim, does not move the selection
        # out from under someone who had already picked a field
        chosen = self.cob_skims_available.currentText()
        self.cob_skims_available.clear()
        self.cob_skims_available.addItems(available)
        if chosen in available:
            self.cob_skims_available.setCurrentText(chosen)

        self.but_add_skim.setEnabled(bool(available) and bool(self.traffic_classes))

    def __change_vdf(self):
        table = self.tbl_vdf_parameters
        table.clearContents()
        parameters = VDF_PARAMETERS.get(self.cob_vdf.currentText().lower(), [])

        # clearContents() empties the cells but keeps the rows, so an unknown function used to
        # leave the previous function's empty rows sitting there
        table.setRowCount(len(parameters))
        for i, par in enumerate(parameters):
            core_item = QTableWidgetItem(par)
            core_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            table.setItem(i, 0, core_item)

            val_item = QLineEdit()
            table.setCellWidget(i, 1, val_item)

            val_fld = QComboBox()
            for x in self.project.network.skimmable_fields():
                val_fld.addItem(x)
            table.setCellWidget(i, 2, val_fld)

    def __graph_for_mode(self, mode_id: str):
        """Returns the graph for a mode, rebuilding it the first time this dialog needs it.

        Graphs are cached in the project, so they outlive this dialog. They also carry a
        snapshot of the links table taken when they were built, and get mutated along the
        way (cost field, skimming, centroid blocking). Reusing the graph left behind by a
        previous dialog means assigning a network that no longer matches the database,
        which is why a failed assignment used to keep failing until the project was closed
        and reopened. Building on first use keeps the retry within the dialog, while still
        sharing the graph between classes of the same mode.

        A mode can be built more than once in a session: the chosen links path pops its
        graph out of the project, so the next class using that mode gets a fresh one
        rather than the copy with links excluded.
        """
        if mode_id not in self.__rebuilt_modes or mode_id not in self.project.network.graphs:
            self.project.network.build_graphs(modes=[mode_id])
            self.__rebuilt_modes.add(mode_id)

        return self.project.network.graphs[mode_id]

    def _create_traffic_class(self, md: str = None):
        mat_name = self.cob_matrices.currentText()
        if not mat_name:
            raise AttributeError("Matrix not set")

        # Stripped, since the name goes on to name the result columns
        class_name = self.ln_class_name.text().strip()
        if not class_name:
            self.qgis_project.iface_error_message(self.tr("Class name cannot be empty"))
            return
        # Folded, because SQLite refuses two columns that differ only by case
        if class_name.lower() in {name.lower() for name in self.traffic_classes}:
            self.qgis_project.iface_error_message(self.tr("Class name already used"))
            return

        matrix = self.project.matrices.get_matrix(mat_name)

        sel = self.tbl_core_list.selectionModel().selectedRows()
        if not sel:
            raise AttributeError("Matrix cores not chosen")
        rows = [s.row() for s in sel if s.column() == 0]
        user_classes = [matrix.names[i] for i in rows]
        matrix.computational_view(user_classes)

        # Columns are named after the cores: relabel with the class name, keep the real ones for the YAML
        self.class_cores[class_name] = user_classes
        if len(user_classes) == 1:
            matrix.view_names = [class_name]
        else:
            matrix.view_names = [f"{class_name}_{core}" for core in user_classes]

        nan_mask = np.isnan(matrix.matrix_view)
        nan_count = np.count_nonzero(nan_mask)
        if nan_count:
            matrix.matrix_view[nan_mask] = 0.0
            value_label = "value" if nan_count == 1 else "values"
            logger.warning(
                f"Replaced {nan_count:,} NaN demand {value_label} with zero in matrix '{mat_name}' "
                f"(core(s): {', '.join(user_classes)})."
            )

        mode = "" if self._from_yaml else self.cob_mode_for_class.currentText()
        mode_id = md if self._from_yaml else self.all_modes[mode]

        graph = self.__graph_for_mode(mode_id)

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
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            table.setItem(idx, i, item)

        but = QPushButton()
        but.setText(self.tr("Remove"))
        but.clicked.connect(self.__remove_class)
        but.setEnabled(False)
        table.setCellWidget(idx, 5, but)

        self.current_modes.append(mode)
        # Seeded before the combos are rebuilt, because refreshing them reads it back
        self.skims[class_name] = []
        self.__edit_skimming_modes()

    def skim_choices(self):
        """Reads the final/blended choices out of the table, keyed by class and field.

        They live nowhere else - `self.skims` only records which fields are being skimmed - so
        they have to be carried across a redraw by hand.
        """
        table = self.skim_list_table
        return {
            (table.item(i, 0).text(), table.item(i, 1).text()): (
                table.cellWidget(i, 2).isChecked(),
                table.cellWidget(i, 3).isChecked(),
            )
            for i in range(table.rowCount())
        }

    def skim_bands(self):
        """The two shades the skimming table bands its classes with, and the text colour to go
        with them, all taken from the table's own palette so that a QGIS colour theme gets
        shades belonging to it rather than a hardcoded pair."""
        palette = self.skim_list_table.palette()
        base = palette.color(QPalette.ColorRole.Base)

        lightness = base.lightness()
        if lightness > 127:
            shifted = lightness - BAND_STEP_FROM_LIGHT
        else:
            shifted = lightness + BAND_STEP_FROM_DARK
        # hue() is -1 on a grey, which fromHsl does not take
        banded = QColor.fromHsl(max(base.hue(), 0), base.saturation(), max(0, min(255, shifted)))

        return [base, banded], palette.color(QPalette.ColorRole.Text)

    def redraw_skim_table(self, choices):
        """Rebuilds the table from `self.skims`, by class and then by field, both alphabetical."""
        table = self.skim_list_table
        table.setRowCount(0)

        # Tuples, so the table is ordered by class first and by field within each class
        rows = sorted((class_name, field) for class_name, fields in self.skims.items() for field in fields)
        table.setRowCount(len(rows))

        # Banded over the classes actually on the table, so that a class with no skims of its
        # own does not eat a shade and leave two neighbouring blocks looking alike
        shades, text_color = self.skim_bands()
        listed = sorted({class_name for class_name, _ in rows})
        bands = {name: shades[i % len(shades)] for i, name in enumerate(listed)}

        for i, (class_name, field) in enumerate(rows):
            band = bands[class_name]
            for column, text in enumerate([class_name, field]):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setBackground(band)
                item.setForeground(text_color)
                table.setItem(i, column, item)

            for column, checked in zip((2, 3), choices.get((class_name, field), (True, True))):
                checkbox = QCheckBox()
                checkbox.setChecked(checked)
                # Cell widgets are painted by the widget, not by the item, so the band has to be
                # put on the check box itself for it to reach the whole row
                checkbox.setAutoFillBackground(True)
                checkbox.setStyleSheet(f"QCheckBox {{ background-color: {band.name()}; }}")
                table.setCellWidget(i, column, checkbox)

        # Every skim owns exactly one row, so an empty table means nothing is being skimmed and
        # `produce_all_outputs` must not go looking for skims to save
        self.skimming = table.rowCount() > 0

    def _add_skimming(self):
        field = self.cob_skims_available.currentText()
        traffic_class = self.traffic_classes[self.cob_skim_class.currentText()]
        name = traffic_class._id
        if not field or field in self.skims[name]:
            # Nothing left to add, or already added: `refresh_available_skims` keeps both off
            # the list, so getting here at all means the two fell out of step
            return

        choices = self.skim_choices()
        self.skims[name].append(field)
        self.redraw_skim_table(choices)
        self.refresh_available_skims()

    def _remove_skimming(self, line):
        """Drops the skim on `line`, which is how a skim added by mistake is taken back.

        Double-clicking columns 2 and 3 never gets here, since the checkboxes sitting in those
        cells take the mouse events themselves. That is the behavior we want: toggling a skim
        between final and blended should not be one stray double-click away from deleting it.
        """
        table = self.skim_list_table
        class_name = table.item(line, 0).text()
        field = table.item(line, 1).text()

        choices = self.skim_choices()

        # Keyed by the class name, which is what `TrafficClass._id` holds
        if field in self.skims.get(class_name, []):
            self.skims[class_name].remove(field)

        self.redraw_skim_table(choices)

        # The field is back up for grabs
        self.refresh_available_skims()

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
            self.qgis_project.iface_error_message(self.tr("Wrong value for link ID"), self.tr("Input error"))
            return

        # Check if link_id exists
        link_id = int(link_id)
        if link_id not in self.__project_links:
            self.qgis_project.iface_error_message(self.tr("Link ID doesn't exist in project"), self.tr("Input error"))
            return

        return link_id

    def build_query(self, qry_name: str = None):
        query_name = qry_name if self._from_yaml else self.input_qry_name.text()

        if len(query_name) == 0 or not query_name:
            self.qgis_project.iface_error_message(self.tr("Missing query name"), self.tr("Input error"))
            return

        if query_name in self.select_links:
            self.qgis_project.iface_error_message(self.tr("Query name already used"), self.tr("Input error"))
            return

        if not self.__current_links:
            self.qgis_project.iface_error_message(self.tr("Please set a link selection"), self.tr("Input error"))
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
        self.exec()

    def job_finished_from_thread(self):
        self.produce_all_outputs()

        self.exit_procedure()

    def run(self):
        if not self.check_data():
            self.qgis_project.iface_error_message(self.error, self.tr("Input error"))
            return

        self.miter = int(self.max_iter.text())
        for q in [self.progressbar, self.progress_label]:
            q.setVisible(True)
        self.progressbar.setRange(0, self.project.network.count_centroids())

        # AequilibraE is the sole authority on whether the network data can be assigned, so we do not
        # pre-check any of it. We just surface whatever the library refuses to accept
        try:
            self.assignment.set_classes(list(self.traffic_classes.values()))
            self.assignment.set_vdf(self.cob_vdf.currentText())
            self.assignment.set_vdf_parameters(self.vdf_parameters)
            self.assignment.set_capacity_field(self.cob_capacity.currentText())
            self.assignment.set_time_field(self.cob_ffttime.currentText())
            self.assignment.max_iter = self.miter
            self.assignment.rgap_target = float(self.rel_gap.text())
            self.assignment.set_algorithm(self.cb_choose_algorithm.currentText())
            self.assignment.log_specification()
        except Exception as e:
            for q in [self.progressbar, self.progress_label]:
                q.setVisible(False)
            self.error = str(e.args[0]) if e.args else str(e)
            logger.error(f"Could not set up the traffic assignment. {e.args}")
            self.qgis_project.iface_error_message(self.error, self.tr("Assignment setup error"))
            return

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

        repeated = self.__repeated_result_fields()
        if repeated:
            self.error = self.tr("More than one class writes the result fields: {}").format(", ".join(repeated))
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

    def __repeated_result_fields(self):
        """Result field names claimed by more than one class, folded as SQLite folds column names."""
        claimed = defaultdict(list)
        for cls in self.traffic_classes.values():
            for name in cls.matrix.view_names:
                claimed[name.lower()].append(name)
        return sorted({name for claims in claimed.values() if len(claims) > 1 for name in claims})

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
            dlg2.exec()

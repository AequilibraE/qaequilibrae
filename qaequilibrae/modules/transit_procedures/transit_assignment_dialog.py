from functools import partial
from os.path import join, dirname

from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.transit import Transit
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem, QAbstractItemView

from qaequilibrae.modules.common_tools import PandasModel
from qaequilibrae.modules.matrix_procedures import list_matrices
from qaequilibrae.modules.transit_procedures.new_period_dialog import NewPeriodDialog
from qaequilibrae.modules.transit_procedures.transit_assignment_procedure import TransitAssignProcedure

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_skimming_assignment.ui"))


class TransitAssignDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.setupUi(self)
        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.transit_data = Transit(self.project)

        self.all_modes = {}
        self.proj_matrices = list_matrices(self.project.matrices.fldr)
        self.skim_fields = []
        self.error = ""
        self.configs = {}

        self.__populate_project_info()

        self.cob_conn_methods.addItems(["Overlapping regions", "Nearest neighbour"])
        self.cob_line_methods.addItems(["Direct", "Connector project match"])
        self.cob_matrices.currentIndexChanged.connect(self.update_matrix_data)
        self.chb_use_graph.toggled.connect(self.__deactivate_graph_configs)

        for table in [self.tbl_periods]:
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.but_add_period.clicked.connect(self.add_period)
        self.but_adds_to_skim.clicked.connect(self.append_to_list)
        self.but_removes_from_skim.clicked.connect(self.removes_fields)

        self.but_assign.clicked.connect(partial(self.run, "assign"))
        self.but_create.clicked.connect(partial(self.run, "create"))

    def __populate_project_info(self):
        self.load_periods_table()

        # Add modes
        with self.project.db_connection as conn:
            res = conn.execute("""select mode_name, mode_id from modes""")

            modes = []
            for x in res.fetchall():
                modes.append(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        self.cob_mode.clear()
        for m in modes:
            self.cob_mode.addItem(m)

        # Add matrix data
        names = self.proj_matrices["name"].tolist()
        self.cob_matrices.addItems(names)
        if names:
            self.update_matrix_data()

        # Add skimming data
        self.skimmeable_fields = [
            "boardings",
            "alightings",
            "inner_transfers",
            "outer_transfers",
            "transfers",
            "trav_time",
            "on_board_trav_time",
            "dwelling_time",
            "egress_trav_time",
            "access_trav_time",
            "walking_trav_time",
            "transfer_time",
            "in_vehicle_trav_time",
            "waiting_time",
        ]
        self.available_skims_table.setRowCount(len(self.skimmeable_fields))
        for i, q in enumerate(self.skimmeable_fields):
            self.available_skims_table.setItem(i, 0, QTableWidgetItem(q))

        # Add travel time and frequency
        flds = ["trav_time", "freq"]  # Use default values?
        for cob in [self.cob_travel_time, self.cob_freq]:
            cob.clear()
            cob.addItems(flds)

    def update_matrix_data(self):
        self.cob_matrix_core.clear()
        file_name = self.proj_matrices.at[self.cob_matrices.currentIndex(), "file_name"]
        mat = AequilibraeMatrix()
        mat.load(join(self.project.matrices.fldr, file_name))
        self.cob_matrix_core.addItems(mat.names)

    def __get_connector_method(self):
        method = self.cob_conn_methods.currentText()
        self.configs["connector_method"] = method.lower().replace(" ", "_")

    def check_inputs(self, action):
        self.__get_connector_method()
        self.configs["period_id"] = self.get_period()
        errors = []  # Initialize a list to collect validation errors

        # Check if there's a graph saved in the project
        self.configs["has_graph"] = self.chb_use_graph.isChecked()
        if self.chb_use_graph.isChecked():
            try:
                self.transit_data.load([self.configs["period_id"]])
            except ValueError:
                errors.append(f"No graph for period_id={self.configs['period_id']} stored in project")

        if action == "create":
            # Check if skim_fields is not empty
            if len(self.skim_fields) == 0:
                errors.append("Add skims to the selection")
            else:
                self.configs["skim_fields"] = self.skim_fields

            # Check if ln_matrix_name is not null
            self.matrix_name = self.ln_matrix_name.text()
            if len(self.matrix_name.replace(" ", "")) == 0:
                errors.append("Check matrix_name")
            else:
                self.configs["matrix_name"] = self.matrix_name

            self.configs["class_name"] = "pt"
        else:
            # Check if ln_transit_class is not empty
            self.class_name = self.ln_transit_class.text()
            if len(self.class_name.replace(" ", "")) == 0:
                errors.append("Check PT class name")
            else:
                self.configs["class_name"] = self.class_name

            # check if ln_result_name is not null
            self.result_name = self.ln_result_name.text()
            if len(self.result_name.replace(" ", "")) == 0:
                errors.append("Check result_name")
            else:
                self.configs["result_name"] = self.result_name

        if not self.error:
            self.error = "\n".join(errors)  # Combine all errors into a single string

    def run(self, action):
        # Deactivate button after click
        button = self.but_create if action == "create" else self.but_assign
        button.setEnabled(False)

        self.check_inputs(action)
        if self.error:
            self.iface.messageBar().pushMessage("Warning", self.error, level=1, duration=10)
            button.setEnabled(True)
            self.error = ""
            return
        else:
            self.pbar = self.pbar_skimming if action == "create" else self.pbar_assignment
            self.label = self.skimming_label if action == "create" else self.assignment_label

            # Graph configs
            self.configs["with_outer_stop_transfers"] = self.chb_outer_stops.isChecked()
            self.configs["with_inner_stop_transfers"] = self.chb_inner_stops.isChecked()
            self.configs["with_walking_edges"] = self.chb_walk_edges.isChecked()
            self.configs["blocking_centroid_flows"] = self.chb_check_centroids.isChecked()
            self.configs["save_graph"] = self.chb_save_graph.isChecked()

            self.configs["line_method"] = self.cob_line_methods.currentText().lower()
            mode = self.cob_mode.currentText()
            self.configs["mode_id"] = self.all_modes[mode]

            # Transit assignment configs
            self.configs["demand_matrix_core"] = "pt" if action == "create" else self.cob_matrix_core.currentText()
            self.configs["time_field"] = "trav_time" if action == "create" else self.cob_travel_time.currentText()
            self.configs["frequency_field"] = "freq" if action == "create" else self.cob_freq.currentText()

            if action == "assign":
                self.configs["mat_name"] = self.proj_matrices.at[self.cob_matrices.currentIndex(), "name"]
                self.configs["mat_core"] = [self.cob_matrix_core.currentText()]

            self.worker_thread = TransitAssignProcedure(
                self.iface.mainWindow(), self.project, self.transit_data, self.configs, action
            )
            self.run_thread()

    def run_thread(self):
        self.worker_thread.signal.connect(self.signal_handler)
        self.worker_thread.doWork()
        self.exit_procedure()

    def add_period(self):
        """Adds new periods to periods table"""
        dlg2 = NewPeriodDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

        if len(dlg2.error) < 1:
            start_time = dlg2.start_time
            end_time = dlg2.end_time
            description = dlg2.description

            periods = self.project.network.periods
            period_id = max(periods.data["period_id"].values) + 1
            periods.new_period(period_id, start_time, end_time, description)
            periods.save()

        self.load_periods_table()

    def load_periods_table(self):
        """Updates periods table view"""
        self.results = self.project.network.periods.data

        self.periods_models = PandasModel(self.results)
        self.tbl_periods.setModel(self.periods_models)

    def get_period(self):
        sel = self.tbl_periods.selectionModel().selectedRows()
        if not sel:
            self.error = "Please select a period"
            return
        row = [s.row() for s in sel if s.column() == 0][0]
        return int(self.results.iloc[row]["period_id"])

    def removes_fields(self):
        """Removes selected fields from skimming"""
        table = self.available_skims_table
        final_table = self.skim_list

        for i in final_table.selectedRanges():
            old_fields = [final_table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                final_table.removeRow(row)
                self.skim_fields.pop(row)

            counter = table.rowCount()
            for field in old_fields:
                table.setRowCount(counter + 1)
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(counter, 0, item1)
                counter += 1

    def append_to_list(self):
        """Adds selected fields to skimming"""
        table = self.available_skims_table
        final_table = self.skim_list

        for i in table.selectedRanges():
            new_fields = [table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for f in new_fields:
                self.skim_fields.append(f)
            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                table.removeRow(row)

            counter = final_table.rowCount()
            for field in new_fields:
                final_table.setRowCount(counter + 1)
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                final_table.setItem(counter, 0, item1)
                counter += 1

    def exit_procedure(self):
        self.close()

    def signal_handler(self, val):
        if val[0] == "start":
            self.pbar.setValue(0)
            self.pbar.setMaximum(val[1])
            self.label.setText(val[2])
        elif val[0] == "update":
            self.pbar.setValue(val[1])
            self.label.setText(val[2])
        elif val[0] == "finished":
            self.pbar.reset()
            self.label.clear()

    def __deactivate_graph_configs(self):
        visualize = not self.chb_use_graph.isChecked()
        self.chb_check_centroids.setEnabled(visualize)
        self.chb_inner_stops.setEnabled(visualize)
        self.chb_outer_stops.setEnabled(visualize)
        self.chb_save_graph.setEnabled(visualize)
        self.chb_walk_edges.setEnabled(visualize)
        self.cob_conn_methods.setEnabled(visualize)
        self.cob_line_methods.setEnabled(visualize)
        self.cob_mode.setEnabled(visualize)
        self.label_1.setEnabled(visualize)
        self.label_2.setEnabled(visualize)
        self.label_3.setEnabled(visualize)

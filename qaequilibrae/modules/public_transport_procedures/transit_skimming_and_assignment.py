from functools import partial
from os.path import join, dirname

import numpy as np
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import TransitAssignment, TransitClass
from aequilibrae.transit import Transit
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem, QAbstractItemView

from qaequilibrae.modules.common_tools import PandasModel
from qaequilibrae.modules.matrix_procedures import list_matrices
from qaequilibrae.modules.public_transport_procedures.new_period_dialog import NewPeriodDialog

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_skimming_assignment.ui"))


class TransitSkimAssign(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.setupUi(self)
        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.transit_data = Transit(self.project)

        self.all_modes = {}
        self.proj_matrices = list_matrices(self.project.matrices.fldr)
        self.skim_fields = []

        self.__populate_project_info()

        self.cob_conn_methods.addItems(["Overlapping regions", "Nearest neighbour"])
        self.cob_line_methods.addItems(["Direct", "Connector project match"])
        self.cob_matrices.currentIndexChanged.connect(self.update_matrix_data)

        for table in [self.tbl_periods]:
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.but_add_period.clicked.connect(self.add_period)
        self.but_adds_to_skim.clicked.connect(self.append_to_list)
        self.but_removes_from_skim.clicked.connect(self.removes_fields)

        self.but_assign.clicked.connect(partial(self.run, "assign"))
        self.but_create.clicked.connect(partial(self.run, "create"))

    def __populate_project_info(self):
        self.load_periods()

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
        self.cob_matrices.addItems(self.proj_matrices["name"].tolist())
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

    def build_graph(self):
        c_method = self.__get_connector_method()
        self.period_id = int(self.get_period())

        graph = self.transit_data.create_graph(
            period_id=self.period_id,
            with_outer_stop_transfers=self.chb_outer_stops.isChecked(),
            with_inner_stop_transfers=self.chb_inner_stops.isChecked(),
            with_walking_edges=self.chb_walk_edges.isChecked(),
            blocking_centroid_flows=self.chb_check_centroids.isChecked(),
            connector_method=c_method,
        )

        # Get project connector configs
        line_method = self.cob_line_methods.currentText().lower()
        mode = self.cob_mode.currentText()
        mode_id = self.all_modes[mode]

        self.project.network.build_graphs()
        graph.create_line_geometry(method=line_method, graph=mode_id)

        if self.chb_save_graph.isChecked():
            self.transit_data.save_graphs(period_ids=[self.period_id])

        # To perform an assignment we need to convert the graph builder into a graph.
        self.transit_graph = graph.to_transit_graph()

    def update_matrix_data(self):
        self.cob_matrix_core.clear()
        file_name = self.proj_matrices.at[self.cob_matrices.currentIndex(), "file_name"]
        mat = AequilibraeMatrix()
        mat.load(join(self.project.matrices.fldr, file_name))
        self.cob_matrix_core.addItems(mat.names)

    def __get_connector_method(self):
        method = self.cob_conn_methods.currentText()
        if method == "Overlapping regions":
            return "overlapping_regions"
        else:
            return "nearest_neighbour"

    def run(self, action):
        # TODO: check inputs before assignment

        self.build_graph()

        mat = self.__build_ones_matrix() if action == "create" else self.__get_matrix()

        class_name = "pt" if action == "create" else self.ln_transit_class.text()
        demand_matrix_core = "pt" if action == "create" else self.cob_matrix_core.currentText()
        time_field = "trav_time" if action == "create" else self.cob_travel_time.currentText()
        frequency_field = "freq" if action == "create" else self.cob_freq.currentText()

        # Create the Transit Class
        assigclass = TransitClass(name=class_name, graph=self.transit_graph, matrix=mat)

        # Create the Transit Assignment Class
        assig = TransitAssignment()
        assig.add_class(assigclass)

        # Set assignment
        assig.set_time_field(time_field)
        assig.set_frequency_field(frequency_field)
        assig.set_skimming_fields(self.skim_fields)
        assig.set_algorithm("os")
        assigclass.set_demand_matrix_core(demand_matrix_core)

        # Perform the assignment
        assig.execute()

        if action == "create":
            assig.get_skim_results()["pt"].export(
                join(self.project.project_base_path, f"matrices/{self.ln_matrix_name.text()}.omx")
            )
        else:
            assig.save_results(table_name=self.ln_result_name.text())
        self.exit_procedure()

    def add_period(self):
        """Adds new periods to periods table"""
        dlg2 = NewPeriodDialog(self.iface, self.project)
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

        self.load_periods()

    def load_periods(self):
        """Updates periods table view"""
        self.results = self.project.network.periods.data

        self.periods_models = PandasModel(self.results)
        self.tbl_periods.setModel(self.periods_models)

    def get_period(self):
        sel = self.tbl_periods.selectionModel().selectedRows()
        if not sel:
            self.iface.messageBar().pushMessage("Warning", "Please select a period", level=1, duration=10)
            return
        row = [s.row() for s in sel if s.column() == 0][0]
        return self.results.iloc[row]["period_id"]

    def __build_ones_matrix(self):
        """Create an array filled with ones."""
        zones = len(self.transit_graph.centroids)

        mat = AequilibraeMatrix()
        mat.create_empty(zones=zones, matrix_names=["pt"], memory_only=True)
        mat.index = self.transit_graph.centroids[:]
        mat.matrices[:, :, 0] = np.ones((zones, zones))
        mat.computational_view()

        return mat

    def __get_matrix(self):
        mat_name = self.proj_matrices.at[self.cob_matrices.currentIndex(), "file_name"]

        mat = AequilibraeMatrix()
        mat.load(join(self.project.matrices.fldr, mat_name))
        mat.computational_view([self.cob_matrix_core.currentText()])

        return mat

    def removes_fields(self):
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

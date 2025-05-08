from os.path import join, dirname

from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.project.database_connection import database_connection
from aequilibrae.transit import Transit, TransitGraphBuilder
from qgis.PyQt import uic
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

        self.__populate_project_info()

        self.cob_conn_methods.addItems(["Overlapping regions", "Nearest neighbour"])
        self.cob_line_methods.addItems(["Direct", "Connector project match"])
        self.cob_matrices.currentIndexChanged.connect(self.update_matrix_data)

        for table in [self.tbl_periods]:
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.but_add_period.clicked.connect(self.add_period)
        # self.but_assign.clicked.connect(self.run_assignment)

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

        graph = self.transit_data(
            with_outer_stop_transfers=self.chb_outer_stops.isChecked(),
            with_inner_stops_transfers=self.chb_inner_stops.isChecked(),
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
            self.transit_data.save_graphs()
            self.transit_data.load()

            # Reading back into AequilibraE
            pt_con = database_connection("transit")
            graph_db = TransitGraphBuilder.from_db(pt_con, self.project.network.periods.default_period.period_id)
            graph_db.vertices.drop(columns="geometry")

        # To perform an assignment we need to convert the graph builder into a graph.
        self.transit_graph = graph.to_transit_graph()

    def update_matrix_data(self):
        self.cob_matrix_core.clear()
        file_name = self.proj_matrices.at[self.cob_matrices.currentIndex(), "file_name"]
        mat = AequilibraeMatrix()
        mat.load(join(self.project.matrices.fldr, file_name))
        self.cob_matrix_core.addItems(mat.names)

    def __get_connector_method(self):
        method = self.cob_direction.currentText()
        if method == "Overlapping regions":
            return "overlapping_regions"
        else:
            return "nearest_neighbour"

    def run_assignment(self):
        if not self.chb_set_assignment.isChecked():
            print()

    def add_period(self):
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
        self.results = self.project.network.periods.data

        self.periods_models = PandasModel(self.results)
        self.tbl_periods.setModel(self.periods_models)

    def get_period(self):
        sel = self.tbl_periods.selectionModel().selectedRows()
        if not sel:
            self.iface.messageBar().pushMessage("Warning", "Please select a period", level=1, duration=10)
            return
        rows = [s.row() for s in sel if s.column() == 0]
        print(rows)

    def exit_procedure(self):
        self.close()

from os.path import join, dirname

from aequilibrae.paths import TransitAssignment, TransitClass
from aequilibrae.transit import Transit
from aequilibrae.transit.transit_graph_builder import TransitGraphBuilder
from qgis.PyQt import uic, QtGui
from qgis.PyQt.QtWidgets import QDialog

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_skimming_assignment.ui"))


class TransitSkimAssign(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.setupUi(self)
        self.project = qgis_project.project
        self.transit_data = Transit(self.project)

        self.__populate_project_info()

        self.cob_conn_methods.addItems(["Overlapping regions", "Nearest neighbour"])
        self.cob_line_methods.addItems(["Direct", "Connector project match"])

    def __populate_project_info(self):
        with self.project.db_connection as conn:
            res = conn.execute("""select mode_name, mode_id from modes""")

            modes = []
            for x in res.fetchall():
                modes.append(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        self.cob_mode.clear()
        for m in modes:
            self.cob_mode.addItem(m)

    def build_graph(self):
        c_method = self.__get_connector_method()

        graph = self.transit_data(
            with_outer_stop_transfers=self.chb_outer_stops.isChecked(),
            with_walking_edges=self.chb_walk_edges.isChecked(),
            blocking_centroid_flows=self.chb_check_centroids.isChecked(),
            connector_method=c_method,
        )

        self.project.network.build_graphs()
        graph.create_line_geometry(method="connector project match", graph="c")
        # self.transit_data.save_graphs()
        # self.transit_data.load()

        # Reading back into AequilibraE
        # pt_con = database_connection("transit")
        # graph_db = TransitGraphBuilder.from_db(pt_con, project.network.periods.default_period.period_id)
        # graph_db.vertices.drop(columns="geometry")

        # To perform an assignment we need to convert the graph builder into a graph.
        self.transit_graph = graph.to_transit_graph()

    def __get_connector_method(self):
        method = self.cob_direction.currentText()
        if method == "Overlapping regions":
            return "overlapping_regions"
        else:
            return "nearest_neighbour"

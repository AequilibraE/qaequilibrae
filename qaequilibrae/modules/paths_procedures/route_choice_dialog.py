import logging
import os
import sys

import geopandas as gpd
import numpy as np
import qgis
from aequilibrae.paths import SubAreaAnalysis, RouteChoice
from aequilibrae.project.database_connection import database_connection
from aequilibrae.utils.db_utils import read_and_close
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout, QCheckBox, QDialog
from qgis._core import QgsFeatureRequest
from qgis.core import QgsMapLayerProxyModel

from qaequilibrae.modules.common_tools import geodataframe_from_layer
from qaequilibrae.modules.common_tools.auxiliary_functions import get_vector_layer_by_name, model_area_polygon
from qaequilibrae.modules.matrix_procedures import list_matrices
from qaequilibrae.modules.paths_procedures.execute_single_dialog import VisualizeSingle
from qaequilibrae.modules.paths_procedures.plot_route_choice import plot_results

sys.modules["qgsmaplayercombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_route_choice.ui"))
logger = logging.getLogger("AequilibraEGUI")


class RouteChoiceDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.qgis_project = qgis_project
        self.matrices = self.project.matrices
        self.setupUi(self)
        self.error = None
        self.matrix = None
        self.cost_function = ""
        self.utility = []

        self.all_modes = {}
        self._pairs = []
        self.link_layer = qgis_project.layers["links"][0]
        self.__kwargs = None

        self.select_links = {}
        self.__current_links = []

        self.__populate_project_info()

        self.__project_nodes = self.project.network.nodes.data.node_id.tolist()
        self.proj_matrices = list_matrices(self.project.matrices.fldr)

        self.cob_algo.addItems(["BFSLE", "Link Penalization", "BFSLE + Link Penalization"])

        self.cob_matrices.currentTextChanged.connect(self.set_show_matrices)
        self.chb_use_all_matrices.toggled.connect(self.set_show_matrices)
        self.but_add_to_cost.clicked.connect(self.add_cost_function)
        self.but_clear_cost.clicked.connect(self.clear_cost_function)
        self.but_perform_assig.clicked.connect(lambda: self.assign_and_save(arg="assign"))
        self.but_build_and_save.clicked.connect(lambda: self.assign_and_save(arg="build"))
        self.but_visualize.clicked.connect(lambda: self.assign_and_save(arg="single"))
        self.chb_set_sub_area.toggled.connect(self.set_sub_area_use)
        self.chb_set_select_link.toggled.connect(self.set_select_link_use)

        self.but_add_qry.clicked.connect(self.add_query)
        self.but_save_qry.clicked.connect(self.save_query)
        self.tbl_selected_links.cellDoubleClicked.connect(self.__remove_select_link_item)
        self.but_clear_qry.clicked.connect(self.__clean_link_selection)

        self.list_matrices()
        self.set_show_matrices()
        self.set_sub_area_use()
        self.set_select_link_use()

    def __populate_project_info(self):
        with read_and_close(database_connection("network")) as conn:
            res = conn.execute("""select mode_name, mode_id from modes""")

            modes = []
            for x in res.fetchall():
                modes.append(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        self.cob_mode.clear()
        for m in modes:
            self.cob_mode.addItem(m)

        flds = self.project.network.skimmable_fields()
        self.cob_net_field.clear()
        self.cob_net_field.addItems(flds)

    def list_matrices(self):
        for _, rec in self.proj_matrices.iterrows():
            if len(rec.WARNINGS) == 0:
                self.cob_matrices.addItem(rec["name"])

    def set_matrix(self):
        if self.cob_matrices.currentIndex() < 0:
            self.matrix = None
            return

        if self.cob_matrices.currentText() in self.qgis_project.matrices:
            self.matrix = self.qgis_project.matrices[self.cob_matrices.currentText()]
            return

        self.matrix = self.qgis_project.project.matrices.get_matrix(self.cob_matrices.currentText())

    def set_show_matrices(self):
        self.tbl_array_cores.setVisible(not self.chb_use_all_matrices.isChecked())
        self.tbl_array_cores.clear()

        self.set_matrix()

        self.tbl_array_cores.setColumnWidth(0, 200)
        self.tbl_array_cores.setColumnWidth(1, 80)
        self.tbl_array_cores.setHorizontalHeaderLabels(["Matrix", "Use?"])

        if self.matrix is not None:
            table = self.tbl_array_cores
            table.setRowCount(self.matrix.cores)
            for i, mat in enumerate(self.matrix.names):
                item1 = QTableWidgetItem(mat)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(i, 0, item1)

                chb1 = QCheckBox()
                chb1.setChecked(True)
                chb1.setEnabled(True)
                table.setCellWidget(i, 1, self.centers_item(chb1))

    def centers_item(self, item):
        cell_widget = QWidget()
        lay_out = QHBoxLayout(cell_widget)
        lay_out.addWidget(item)
        lay_out.setAlignment(Qt.AlignCenter)
        lay_out.setContentsMargins(0, 0, 0, 0)
        cell_widget.setLayout(lay_out)
        return cell_widget

    def add_cost_function(self):
        params = self.ln_parameter.text()
        valid_params = self.__check_parameter_value(params)

        if not valid_params:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1)
            return

        if len(self.cost_function) > 0 and self.parameter >= 0:
            self.cost_function += " + "
        elif len(self.cost_function) > 0 and self.parameter < 0:
            params = params.replace("-", " - ")

        self.cost_function += f"{params} * {self.cob_net_field.currentText()}"
        self.txt_cost_func.setText(self.cost_function)

        self.utility.extend([(self.parameter, self.cob_net_field.currentText())])

    def clear_cost_function(self):
        self.txt_cost_func.clear()

        self.cost_function = ""

    def exit_procedure(self):
        self.close()

    def __check_parameter_value(self, par):
        # parameter cannot be null
        if len(par) == 0:
            self.error = "Check parameter value."
            return False

        # parameter needs to be numeric
        if not par.replace(".", "").replace("-", "").isdigit():
            self.error = "Wrong value in parameter."
            return False

        self.parameter = float(par)
        return True

    def configure_graph(self):
        mode = self.cob_mode.currentText()
        mode_id = self.all_modes[mode]
        if mode_id not in self.project.network.graphs:
            self.project.network.build_graphs(modes=[mode_id])

        graph = self.project.network.graphs[mode_id]

        field = np.zeros((1, graph.network.shape[0]))
        for idx, (par, col) in enumerate(self.utility):
            field += par * graph.network[col].array

        graph.network = graph.network.assign(utility=0)
        graph.network["utility"] = field.reshape(graph.network.shape[0], 1)

        if self.chb_chosen_links.isChecked():
            graph = self.project.network.graphs.pop(mode_id)
            idx = self.link_layer.dataProvider().fieldNameIndex("link_id")
            remove = [feat.attributes()[idx] for feat in self.link_layer.selectedFeatures()]
            graph.exclude_links(remove)

        graph.set_blocked_centroid_flows(self.chb_check_centroids.isChecked())

        return graph

    def __get_parameters(self, arg):
        # parameter needs to be numeric
        if not self.max_routes.text().isdigit():
            self.error = "Max. routes needs to be a numeric integer value"
        max_routes = int(self.max_routes.text())

        if not self.max_depth.text().isdigit():
            self.error = "Max. depth needs to be a numeric integer value"
        max_depth = int(self.max_depth.text())

        if max_depth <= 0 and max_routes <= 0:
            self.error = "One of max. routes or max. depth has to be greater than 0"

        # Check cutoff
        if not self.ln_cutoff.text().replace(".", "").isdigit():
            self.error = "Probability cutoff needs to be a float number"

        cutoff = float(self.ln_cutoff.text())
        if cutoff < 0 or cutoff > 1:
            self.error = "Probability cutoff assumes values between 0 and 1"

        # Check penalty
        if not self.penalty.text().replace(".", "").isdigit():
            self.error = "Penalty needs to be a float number"

        # Check PSL(beta)
        if not self.ln_psl.text().replace(".", "").isdigit():
            self.error = "PSL (beta) needs to be a float number"

        self.__kwargs = {
            "max_routes": max_routes,
            "max_depth": max_depth,
            "penalty": float(self.penalty.text()),
            "cutoff_prob": cutoff,
            "beta": float(self.ln_psl.text()),
        }

        if arg == "assign" and not self.chb_save_choice_set.isChecked():
            self.__kwargs["store_results"] = False
        else:
            self.__kwargs["store_results"] = True

        algo = self.cob_algo.currentText().lower()
        self.__algo = "bfsle" if algo == "bfsle" else "lp"

    def __validate_node_id(self, node_id: str):
        # Check if we have only numbers
        if not node_id.isdigit():
            self.error = self.tr("Wrong input value for node ID")
            return

        # Check if node_id exists
        node_id = int(node_id)
        if node_id not in self.__project_nodes:
            self.error = self.tr("Node ID doesn't exist in project")
            return

        return node_id

    def _build_rc(self, graph):
        rc = RouteChoice(graph)
        rc.set_choice_set_generation(self.__algo, **self.__kwargs)
        return rc

    def _open_visualize_single_dlg(self, graph):
        self.dlg2 = VisualizeSingle(
            qgis.utils.iface.mainWindow(),
            graph,
            self.__algo,
            self.__kwargs,
            self.from_node,
            self.to_node,
            float(self.ln_demand.text()),
            self.link_layer,
        )
        self.dlg2.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.dlg2.show()
        self.dlg2.open()
        # see note in https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/QDialog.html#PySide2.QtWidgets.PySide2.QtWidgets.QDialog.exec_

    def assign_and_save(self, arg):
        if arg == "single":
            self.from_node = self.__validate_node_id(self.node_from.text())
            self.to_node = self.__validate_node_id(self.node_to.text())

            demand = self.ln_demand.text()
            if not demand.replace(".", "").isdigit():
                self.error = "Wrong input value for demand"

        else:
            self.set_matrix()

            if self.chb_use_all_matrices.isChecked():
                matrix_cores_to_use = self.matrix.names
            else:
                matrix_cores_to_use = []
                for i, mat in enumerate(self.matrix.names):
                    if self.tbl_array_cores.cellWidget(i, 1).findChildren(QCheckBox)[0].isChecked():
                        matrix_cores_to_use.append(mat)

            if len(matrix_cores_to_use) > 0:
                self.matrix.computational_view(matrix_cores_to_use)
            else:
                self.error = "Check matrices inputs"

        self.__get_parameters(arg)

        if self.error:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1)
            return

        graph = self.configure_graph()

        nodes_of_interest = (
            np.array([self.from_node, self.to_node], dtype=np.int64) if arg == "single" else graph.centroids
        )
        graph.prepare_graph(nodes_of_interest)
        graph.set_graph("utility")

        if self.chb_set_sub_area.isChecked():
            zones = self.__get_project_zones()  # Set selected zones
            self.matrix = self.set_sub_area(graph, zones)

            # Rebuild graph for external ODs
            new_centroids = np.unique(self.matrix.reset_index()[["origin id", "destination id"]].to_numpy().reshape(-1))
            graph.prepare_graph(new_centroids)
            graph.set_graph("utility")

        rc = self._build_rc(graph)

        if arg == "single":
            _ = rc.execute_single(self.from_node, self.to_node, float(demand))

            plot_results(rc.get_results().to_pandas(), self.from_node, self.to_node, self.link_layer)

            self._open_visualize_single_dlg(graph)

        else:
            rc.add_demand(self.matrix)
            rc.prepare()

            # Set folder location to save route choice sets
            if arg == "build" or self.chb_save_choice_set.isChecked():
                folder = self.__check_folder_exists()
                rc.set_save_routes(folder)

            # Set selected link
            if self.chb_set_select_link.isChecked():
                rc.set_select_links(self.select_links)

            # Run route choice with assignment or not
            assig = True if arg == "assign" else False
            rc.execute(perform_assignment=assig)

            self.__rc_name = self.ln_rc_output.text()

            # Save assignment flows to results database
            if arg == "assign":
                # Save select link analysis outputs (matrix and result)
                if self.chb_set_select_link.isChecked():
                    rc.save_select_link_flows(self.ln_mat_name.text())
                else:
                    rc.save_link_flows(self.__rc_name)

            # Save sub-area demand matrix
            if self.chb_set_sub_area.isChecked():
                folder = self.__check_folder_exists()
                self.matrix.to_parquet(os.path.join(folder, f"{self.__rc_name}.parquet"))

            message = f"Route choice sets saved to {self.project.project_base_path}"
            qgis.utils.iface.messageBar().pushMessage("Success", message, level=3, duration=10)

        self.exit_procedure()

    def __check_folder_exists(self):
        rc_folder = os.path.join(self.project.project_base_path, "route_choice")
        if not os.path.isdir(rc_folder):
            os.mkdir(rc_folder)
        return rc_folder

    ###### For sub-area analysis

    def set_sub_area(self, graph, zones):
        sub_area = SubAreaAnalysis(graph, zones, self.matrix)
        sub_area.rc.set_choice_set_generation(self.__algo, **self.__kwargs)
        sub_area.rc.execute(perform_assignment=True)

        # I don't know why but origin and destination ID are assumed to be strings, which is
        # raising an error when assembling the COO Matrix. We use infer objects to ensure that
        # indexes are numeric integers
        demand = sub_area.post_process().reset_index().infer_objects()
        demand = demand.groupby(["origin id", "destination id"]).sum()
        return demand

    def set_sub_area_use(self):
        for item in [self.cob_zoning_layer, self.chb_selected_zones, self.label_24]:
            item.setEnabled(self.chb_set_sub_area.isChecked())

        self.chb_set_select_link.setEnabled(not self.chb_set_sub_area.isChecked())
        self.cob_zoning_layer.setFilters(QgsMapLayerProxyModel.PolygonLayer)

    def __get_project_zones(self):
        zones = get_vector_layer_by_name(self.cob_zoning_layer.currentText())

        if self.chb_selected_zones.isChecked():
            zones = zones.materialize(QgsFeatureRequest().setFilterFids(zones.selectedFeatureIds()))

        zones_gdf = geodataframe_from_layer(zones)

        poly, crs = model_area_polygon(zones_gdf)

        return gpd.GeoDataFrame(geometry=[poly], crs=crs)

    ###### For select link analysis

    def set_select_link_use(self):
        for item in [
            self.ln_qry_name,
            self.ln_link_id,
            self.cob_direction,
            self.but_add_qry,
            self.but_save_qry,
            self.but_clear_qry,
            self.tbl_selected_links,
            self.gridGroupBox,
            self.label_21,
            self.label_22,
            self.label_23,
        ]:
            item.setEnabled(self.chb_set_select_link.isChecked())

        self.cob_direction.addItems(["AB", "Both", "BA"])

        self.chb_set_sub_area.setEnabled(not self.chb_set_select_link.isChecked())

    def add_query(self):
        link_id = int(self.ln_link_id.text())

        direction = self.cob_direction.currentText()

        if direction == "AB":
            self.__current_links.extend([(link_id, 1)])
        elif direction == "BA":
            self.__current_links.extend([(link_id, -1)])
        else:
            self.__current_links.extend([(link_id, 0)])

    def save_query(self):
        query_name = self.ln_qry_name.text()

        if len(query_name) == 0 or not query_name:
            self.error = self.tr("Missing query name")

        if query_name in self.select_links:
            self.error = self.tr("Query name already used")

        if not self.__current_links:
            self.error = self.tr("Please set a link selection")

        if self.error:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1)
            return

        self.select_links[query_name] = [self.__current_links]

        self.tbl_selected_links.clearContents()
        self.tbl_selected_links.setRowCount(len(self.select_links.keys()))

        for i, (name, links) in enumerate(self.select_links.items()):
            self.tbl_selected_links.setItem(i, 0, QTableWidgetItem(str(links)))
            self.tbl_selected_links.setItem(i, 1, QTableWidgetItem(str(name)))

        self.__current_links = []

    def __remove_select_link_item(self, line):
        key = list(self.select_links.keys())[line]
        self.tbl_selected_links.removeRow(line)

        self.select_links.pop(key)

    def __clean_link_selection(self):
        self.ln_qry_name.clear()
        self.ln_link_id.clear()
        self.cob_direction.setCurrentIndex(0)
        self.__current_links = []

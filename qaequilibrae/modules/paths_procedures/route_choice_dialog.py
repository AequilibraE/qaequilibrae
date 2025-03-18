import logging
import os
import sys

import geopandas as gpd
import qgis
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
from qaequilibrae.modules.paths_procedures.execute_single_dialog import ExecuteSingleDialog
from qaequilibrae.modules.paths_procedures.plot_route_choice import plot_results
from qaequilibrae.modules.paths_procedures.route_choice_procedure import RouteChoiceProcedure

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
        self.parameters = {}

        self.select_links = {}
        self.__current_links = []

        self.__populate_project_info()

        self.__project_nodes = self.project.network.nodes.data.node_id.tolist()
        self.proj_matrices = list_matrices(self.project.matrices.fldr)

        self.cob_algo.addItems(["BFSLE", "Link Penalization", "BFSLE with Link Penalization"])
        self.cob_direction.addItems(["AB", "Both", "BA"])

        self.cob_matrices.currentTextChanged.connect(self.set_show_matrices)
        self.chb_use_all_matrices.toggled.connect(self.set_show_matrices)
        self.but_add_to_cost.clicked.connect(self.add_cost_function)
        self.but_clear_cost.clicked.connect(self.clear_cost_function)
        self.but_perform_assig.clicked.connect(self.execute_assign)
        self.but_build_and_save.clicked.connect(self.execute_build)
        self.but_visualize.clicked.connect(self.execute_single)
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

        def centers_item(item):
            cell_widget = QWidget()
            lay_out = QHBoxLayout(cell_widget)
            lay_out.addWidget(item)
            lay_out.setAlignment(Qt.AlignCenter)
            lay_out.setContentsMargins(0, 0, 0, 0)
            cell_widget.setLayout(lay_out)
            return cell_widget

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
                table.setCellWidget(i, 1, centers_item(chb1))

    def add_cost_function(self):
        params = self.ln_parameter.text()

        # parameter needs to be numeric and cannot be null
        if not params.replace(".", "").replace("-", "").isdigit():
            self.error = "Check parameter value input"

        if self.error:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=10)
            return

        parameter = float(params)

        if len(self.cost_function) > 0 and parameter >= 0:
            self.cost_function += " + "
        elif len(self.cost_function) > 0 and parameter < 0:
            params = params.replace("-", " - ")

        self.cost_function += f"{params} * {self.cob_net_field.currentText()}"
        self.txt_cost_func.setText(self.cost_function)

        self.utility.extend([(parameter, self.cob_net_field.currentText())])

    def clear_cost_function(self):
        self.txt_cost_func.clear()

        self.cost_function = ""

    def _get_graph_config(self):
        mode = self.cob_mode.currentText()
        mode_id = self.all_modes[mode]

        idx = self.link_layer.dataProvider().fieldNameIndex("link_id")
        remove = [feat.attributes()[idx] for feat in self.link_layer.selectedFeatures()]

        self.parameters["graph"] = {
            "mode_id": mode_id,
            "use_chosen_links": self.chb_chosen_links.isChecked(),
            "links_to_remove": remove,
            "block_centroid_flows": self.chb_check_centroids.isChecked(),
            "utility": self.utility,
        }

    ###### For sub-area analysis
    def set_sub_area_use(self):
        for item in [self.cob_zoning_layer, self.chb_selected_zones, self.label_24]:
            item.setEnabled(self.chb_set_sub_area.isChecked())

        self.chb_set_select_link.setEnabled(not self.chb_set_sub_area.isChecked())
        # Only polygon layers as zones
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
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=10)
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

    # Validate model inputs
    def _validate_inputs(self):
        cob_algo = self.cob_algo.currentText().lower()
        algo = "bfsle" if "bfsle" in cob_algo else "lp"

        # Check parameter data input
        # parameter needs to be numeric
        if not self.max_routes.text().isdigit():
            self.error = "Max. routes needs to be a positive integer value"

        if not self.max_depth.text().isdigit():
            self.error = "Max. depth needs to be a positive integer value"

        # Check cutoff
        if not self.ln_cutoff.text().replace(".", "").isdigit():
            self.error = "Probability cutoff needs to be a positive float value"

        # Check penalty
        if not self.penalty.text().replace(".", "").isdigit():
            self.error = "Penalty needs to be a positive float value"

        # Check PSL(beta)
        if not self.ln_psl.text().replace(".", "").isdigit():
            self.error = "PSL (beta) needs to be a positive float value"

        # Check saving file names too

        # We return in case of error because in the we'll modify the text input to numbers
        if self.error:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=10)
            return

        # Check parameter values
        max_routes = int(self.max_routes.text())
        max_depth = int(self.max_depth.text())
        if max_depth <= 0 and max_routes <= 0:
            self.error = "One of max. routes or max. depth has to be greater than 0"

        cutoff = float(self.ln_cutoff.text())
        if cutoff > 1:
            self.error = "Probability cutoff assumes values between 0.0 and 1.0"

        penalty = float(self.penalty.text())
        if cob_algo in ["bfsle with link penalization"] and penalty <= 1.0:
            self.error = "Penalty needs to be greater than 1.0 for BFSLE with Link Penalization"

        if self.job == "execute_single":
            nds = {"node_from": self.node_from.text(), "node_to": self.node_to.text()}
            for node in nds.values():
                # Check node ID is numeric
                if not node.isdigit():
                    self.error = "Wrong input value for node ID"

                # Check if node_id exists
                node_id = int(node)
                if node_id not in self.__project_nodes:
                    self.error = f"Node ID {node_id} doesn't exist in project"

            # Check for execute_single demand
            demand = self.ln_demand.text()
            if not demand.replace(".", "").isdigit():
                self.error = "Wrong input value for demand"

        if self.job in ["assign", "build"]:
            # Let's check up matrix data here
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

        if self.error:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Input error"), self.error, level=1, duration=10)
            return

        # Populate with our model parameters
        self.parameters = {
            "algorithm": algo,
            "kwargs": {
                "max_routes": max_routes,
                "max_depth": max_depth,
                "penalty": penalty,
                "cutoff_prob": cutoff,
                "beta": float(self.ln_psl.text()),
                "store_results": True,
            },
            "set_select_links": self.chb_set_select_link.isChecked(),
            "select_links": self.select_links,
            "save_choice_sets": self.chb_save_choice_set.isChecked(),
        }

        if self.chb_set_sub_area.isChecked():
            self.parameters["set_sub_area"] = True
            self.parameters["zones"] = self.__get_project_zones()
        else:
            self.parameters["set_sub_area"] = False

        if self.job == "build" or self.parameters["save_choice_sets"] or self.parameters["set_sub_area"]:
            rc_folder = os.path.join(self.project.project_base_path, "route_choice")
            if not os.path.isdir(rc_folder):
                os.mkdir(rc_folder)
            self.parameters["rc_folder"] = rc_folder

        self.parameters["matrix"] = float(demand) if self.job == "execute_single" else self.matrix

        if self.job == "execute_single":
            for key, value in nds.items():
                self.parameters[key] = int(value)

        if self.job == "assign" and not self.parameters["save_choice_sets"]:
            self.parameters["kwargs"]["store_results"] = False

    def execute_single(self):
        self.job = "execute_single"
        self.run()

    def execute_assign(self):
        self.job = "assign"
        self.run()

    def execute_build(self):
        self.job = "build"
        self.run()

    def run(self):
        self._validate_inputs()
        self._get_graph_config()

        if self.error:
            return

        self.worker_thread = RouteChoiceProcedure(
            qgis.utils.iface.mainWindow(), self.project, self.job, self.parameters
        )
        self.run_thread()

    def run_thread(self):
        self.worker_thread.signal.connect(self.signal_handler)
        self.worker_thread.start()
        self.exec_()

    def signal_handler(self, val):
        if val[0] == "finished":
            message = None

            if self.job == "assign":
                self.worker_thread.rc.save_link_flows(self.ln_rc_output.text())

            if self.parameters["set_select_links"]:
                message = f"Route choice sets saved to {self.project.project_base_path}"
                self.worker_thread.rc.save_select_link_flows(self.ln_mat_name.text())

            if self.parameters["set_sub_area"]:
                self.worker_thread.matrix.to_parquet(
                    os.path.join(self.parameters["rc_folder"], f"{self.ln_rc_output.text()}.parquet")
                )

            if self.job == "build" or self.parameters["save_choice_sets"]:
                message = f"Route choice sets saved to {self.project.project_base_path}"

            if message:
                qgis.utils.iface.messageBar().pushMessage("Success", message, level=3, duration=10)

            if self.job == "execute_single":
                res = self.worker_thread.rc.get_results().to_pandas()
                plot_results(res, self.parameters["node_from"], self.parameters["node_to"], self.link_layer)

            self.exit_procedure()

    def exit_procedure(self):
        if self.job == "execute_single":
            dlg2 = ExecuteSingleDialog(
                qgis.utils.iface.mainWindow(),
                self.worker_thread.graph,
                self.link_layer,
                self.parameters,
            )
            dlg2.show()
            dlg2.open()
            # see note in https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/QDialog.html#PySide2.QtWidgets.PySide2.QtWidgets.QDialog.exec_

        self.close()

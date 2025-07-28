import os
from math import ceil
from random import choice

import numpy as np
import pandas as pd
from aequilibrae.paths import Graph
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDialog
from qgis.core import QgsLinePatternFillSymbolLayer, QgsProject, Qgis
from qgis.core import QgsStyle, QgsVectorLayerJoinInfo, QgsRuleBasedRenderer, QgsSymbol

from qaequilibrae.modules.common_tools import layer_from_dataframe
from qaequilibrae.modules.common_tools.geodataframe_from_data_layer import geodataframe_from_layer

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_skim_viewer.ui"))


class SkimViewerDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.setupUi(self)

        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.qgis_project = qgis_project
        self.all_modes = {}
        self.layer = self.iface.activeLayer()
        self.graph = None
        self.idx = None
        self.error = None

        # Check if we have an active layer, otherwise raises an error
        if self.layer is not None:
            # We get the layer ID to check if it was removed from the layers' panel
            self.__layer_id = self.layer.id()

            self._lyr = "zones" if self.layer.name() == "zones" else "nodes"
            self.layer_col = "zone_id" if self.layer.name() == "zones" else "node_id"

            QgsProject.instance().layersRemoved.connect(self.__on_layer_removed)
        else:
            self.error = "Please set an active layer to proceed"
            self.iface.messageBar().pushMessage(
                self.tr("Input error"), self.error, level=Qgis.MessageLevel.Critical, duration=10
            )
            self.__disable_fields()  # We disable all QDialog objects if there's no active layer set
            return

        # Layer fields
        default_style = QgsStyle().defaultStyle()
        self.cob_color.addItems(list(default_style.colorRampNames()))

        self._nodes = self.project.network.nodes.data["node_id"].tolist()
        self._zones = list(self.project.zoning.all_zones().keys())

        # Randomly populate the start ID if we don't have a selected layer feature
        if not self.layer.selectedFeatures():
            idx = choice(self._zones) if self._lyr == "zones" else choice(self._nodes)
            self.line_start_id.setText(str(idx))

        if self.idx:
            self.layer.selectionChanged.connect(self.recompute_after_selection)

        # Check if layer links is in the layers tab.
        self.__prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]

        with self.project.db_connection as conn:
            centroids = pd.read_sql("select node_id from nodes where is_centroid=1", con=conn).node_id.to_numpy()

        self.centroids = centroids if centroids.size != 0 else None

        self.__no_skimming_fields = [
            "link_id",
            "a_node",
            "b_node",
            "direction",
            "id",
            "__supernet_id__",
            "__compressed_id__",
        ]

        # Graph config
        with self.project.db_connection as conn:
            res = conn.execute("""SELECT mode_name, mode_id FROM modes""")
            for x in res.fetchall():
                self.cob_modes.addItem(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        self.but_plot.clicked.connect(self.run)
        self.cob_minimizing.currentIndexChanged.connect(self.update_cost_field)
        self.cob_skim.currentIndexChanged.connect(self.update_skim_field)
        self.block_paths.toggled.connect(self.update_block_flow)

        self.configure_skim_fields()

    def __on_layer_removed(self, layer_ids):
        if self.__layer_id in layer_ids:
            self.__disable_fields()
            self._show_layer_removed_message()

    def _show_layer_removed_message(self):
        self.error = self.tr("Critical layer for Skim Viewer removed from the layers' panel")
        self.iface.messageBar().pushMessage(self.tr("Error"), self.error, level=Qgis.MessageLevel.Critical, duration=10)

    def __disable_fields(self):
        dialog_elements = [
            self.block_paths,
            self.cob_minimizing,
            self.cob_modes,
            self.cob_skim,
            self.label_1,
            self.label_2,
            self.label_3,
            self.chb_invert,
            self.cob_color,
            self.label_5,
            self.label_6,
            self.line_start_id,
            self.but_plot,
            self.graph_config,
            self.layer_config,
        ]

        for element in dialog_elements:
            element.setVisible(False)

    def configure_skim_fields(self):
        self.cob_minimizing.clear()
        self.cob_skim.clear()

        if "links" in self.__prj_layers:
            layer = self.qgis_project.layers["links"][0]

            network = geodataframe_from_layer(layer)
            network.columns = [x.lower() for x in network.columns]

            self.graph = Graph()
            self.graph.network = network
            self.graph.prepare_graph(self.centroids)

            self._skimmeable_fields = [x for x in self.graph.graph.columns if x not in self.__no_skimming_fields]
        else:
            self._skimmeable_fields = self.project.network.skimmable_fields()

        for skim in self._skimmeable_fields:
            self.cob_minimizing.addItem(skim)
            self.cob_skim.addItem(skim)

    def exit_procedure(self):
        QgsProject.instance().layersRemoved.disconnect(self.__on_layer_removed)
        self.layer.selectionChanged.disconnect()
        self.close()

    def configure_graph(self):
        if not self.graph:
            mode = self.all_modes[self.cob_modes.currentText()]
            self.project.network.build_graphs(modes=[mode])
            self.graph = self.project.network.graphs[mode]

            # We prepare the graph to set all nodes as centroids
            if self._lyr == "nodes":
                self.graph.prepare_graph(self.graph.all_nodes)

        self.graph.set_blocked_centroid_flows(self.block_paths.isChecked())

        self.graph.set_graph(self.cob_minimizing.currentText())
        self.graph.set_skimming(self.cob_skim.currentText())

        self.indices = self.graph.all_nodes.astype(np.int32)
        self.idx_position = dict(zip(self.indices, np.arange(len(self.indices))))

    def compute_skims(self, start_node):
        res = self.graph.compute_path(start_node, self.indices[-1])
        self.data_to_show = res._skimming_array[:-1]

        self.set_data()

    def map_ranges(self, fld, layer, color_ramp_name):
        from qaequilibrae.modules.gis.color_ramp_shades import color_ramp_shades

        # First, we check if we have numeric values in our column
        all_values = []
        for _, f in enumerate(layer.getFeatures()):
            all_values.append(f["skim_viewer_data"])

        all_values = np.array(all_values, dtype=np.float32)
        values = np.unique(all_values)

        # We remove infs and nans to find the largest numeric value
        values = values[~np.isnan(values)]
        values = values[values < 3.39e38]
        values = values[values >= -3.40e38]

        #
        num_steps = min(max(values.shape[0], 1), 9) if values.shape[0] > 0 else 1
        max_metric = max(values) if values.shape[0] >= 1 else 0

        #
        values = [ceil(i * (max_metric / num_steps)) for i in range(1, num_steps + 1)]
        values = [0, 0.000000000001] + values
        invert = self.chb_invert.isChecked()
        color_ramp = color_ramp_shades(color_ramp_name, num_steps, invert)

        # Set the hatch background white if active layer is zones, otherwise use black for nodes
        color = QColor(255, 255, 255) if self._lyr == "zones" else QColor(0, 0, 0)

        # Create Rule-Based renderer
        root_rule = QgsRuleBasedRenderer.Rule(None)

        # Rule 1: NaN values
        hatch_symbol = self.create_hatch(layer, color)
        nan_expression = f'"{fld}" IS NULL OR "{fld}" = \'nan\' OR "{fld}" = \'NaN\''
        nan_rule = QgsRuleBasedRenderer.Rule(hatch_symbol, filterExp=nan_expression, label="NaN Values")
        root_rule.appendChild(nan_rule)

        # Rule 2: Inf values
        hatch_symbol = self.create_hatch(layer, color)
        inf_expression = (
            f"\"{fld}\" = 'inf' OR \"{fld}\" = '+inf' OR \"{fld}\" = '-inf' OR "
            f'"{fld}" >= 3.40e38 OR "{fld}" <= -3.40e38'
        )
        inf_rule = QgsRuleBasedRenderer.Rule(hatch_symbol, filterExp=inf_expression, label="Inf Values")
        root_rule.appendChild(inf_rule)

        # Remaining rules
        for i in range(num_steps + 1):
            myColour = color_ramp[i]
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(myColour)
            symbol.setOpacity(1)

            # Create expression for the range
            if i == 0:
                expression = f'"{fld}" = 0'
                label = "0"
                description = "0"
            elif i == 1:
                expression = f'"{fld}" > 0 AND "{fld}" <= {values[i + 1]}'
                label = f"Up to {values[i + 1]}"
                description = f"Range 0 -{values[i + 1]} (not included)"
            elif i > 1 and i <= (num_steps - 1):
                expression = f'"{fld}" >= {values[i]} AND "{fld}" < {values[i + 1]}'
                label = f"{values[i]}-{values[i + 1]}"
                description = f"Range {values[i]}-{values[i + 1]} (not included)"
            else:
                expression = f'"{fld}" >= {values[i]} AND "{fld}" <= {values[i + 1]}'
                label = f"{values[i]}-{values[i + 1]}"
                description = f"Range {values[i]}-{values[i + 1]} (included)"

            # Create rule
            range_rule = QgsRuleBasedRenderer.Rule(symbol, 0, 0, expression, label, description)
            root_rule.appendChild(range_rule)

        # Create the renderer
        renderer = QgsRuleBasedRenderer(root_rule)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

        self.iface.mapCanvas().setExtent(layer.extent())
        self.iface.mapCanvas().refresh()

    def create_hatch(self, layer, color):
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(color)
        symbol.setOpacity(1)

        # Create line pattern fill layer (hatch)
        hatch_layer = QgsLinePatternFillSymbolLayer()

        # Set hatch properties
        hatch_layer.setDistance(2.0)  # Distance between lines
        hatch_layer.setAngle(45.0)  # Angle of lines (45 degrees)

        # Create the line symbol for the hatch pattern
        line_symbol = hatch_layer.subSymbol()
        line_layer = line_symbol.symbolLayer(0)

        # Customize the line appearance
        line_layer.setWidth(0.5)  # Line width
        line_layer.setColor(QColor(0, 0, 0))  # Black color

        # Add the hatch layer to the symbol
        symbol.appendSymbolLayer(hatch_layer)

        return symbol

    def make_join(self, base_layer, join_field, metric_layer):
        lien = QgsVectorLayerJoinInfo()
        lien.setJoinFieldName(join_field)
        lien.setTargetFieldName(join_field)
        lien.setJoinLayerId(metric_layer.id())
        lien.setUsingMemoryCache(True)
        lien.setJoinLayer(metric_layer)
        lien.setPrefix("skim_viewer_")
        base_layer.addJoin(lien)

    def remove_mapping_layer(self):
        self.remove_data_layer()
        for lien in self.layer.vectorJoins():
            self.layer.removeJoin(lien.joinLayerId())
        self.mapping_layer = None
        self.layer.triggerRepaint()

    def remove_data_layer(self):
        active_layers = [name.name() for name in QgsProject.instance().mapLayers().values()]
        if "skim_viewer" in active_layers:
            layer = QgsProject.instance().mapLayersByName("skim_viewer")[0]
            QgsProject.instance().removeMapLayers([layer.id()])
            self.iface.mapCanvas().refresh()

            self.mapping_layer = None

    def map_dt(self, dt):
        self.remove_mapping_layer()
        df = pd.DataFrame({self.layer_col: self.indices, "data": dt})
        self.mapping_layer = layer_from_dataframe(df, "skim_viewer")
        self.make_join(self.layer, self.layer_col, self.mapping_layer)

        color_ramp_name = self.cob_color.currentText()
        self.map_ranges("skim_viewer_data", self.layer, color_ramp_name)

        self.iface.setActiveLayer(self.layer)

    def set_data(self):
        dt = self.data_to_show.reshape(self.graph.num_nodes)
        self.map_dt(dt)

    def recompute_after_selection(self):
        selected_features = self.layer.selectedFeatures()
        self.idx = [feature[self.layer_col] for feature in selected_features][0]

        self.compute_skims(self.idx)

    def update_skim_field(self):
        if self.idx:
            self.graph.set_skimming(self.cob_skim.currentText())
            self.compute_skims(self.idx)

    def update_cost_field(self):
        if self.idx:
            self.graph.set_graph(self.cob_minimizing.currentText())
            self.compute_skims(self.idx)

    def update_block_flow(self):
        if self.idx:
            self.graph.set_blocked_centroid_flows(self.block_paths.isChecked())
            self.compute_skims(self.idx)

    def _check_start_id(self):
        try:
            selected_features = self.layer.selectedFeatures()
            self.idx = [feature[self.layer_col] for feature in selected_features][0]
        except IndexError:
            idx = self.line_start_id.text().replace(" ", "")

            if not idx.isdigit():
                self.error = "Start ID needs to be a positive integer value"
                return

            self.idx = int(idx)

            if self._lyr == "nodes" and self.idx not in self._nodes:
                self.error = "Start ID relates to a non-existing node"

            if self._lyr == "zones" and self.idx not in self._zones:
                self.error = "Start ID relates to a non-existing zone"

    def run(self):
        self._check_start_id()

        if self.error:
            self.iface.messageBar().pushMessage(
                self.tr("Input error"), self.error, level=Qgis.MessageLevel.Critical, duration=10
            )
            self.idx = None
            self.error = None
            return

        self.configure_graph()

        self.layer.selectionChanged.connect(self.recompute_after_selection)

        self.compute_skims(self.idx)

        self.cob_color.setEnabled(False)
        self.chb_invert.setEnabled(False)

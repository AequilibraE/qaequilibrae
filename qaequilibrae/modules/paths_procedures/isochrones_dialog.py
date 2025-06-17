from math import ceil
import os

import numpy as np
import pandas as pd
from aequilibrae.paths import NetworkSkimming, SkimResults
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtWidgets import QDialog, QAbstractItemView
from qgis.core import QgsStyle, QgsVectorLayerJoinInfo, QgsRuleBasedRenderer, QgsSymbol
from qgis.core import QgsLinePatternFillSymbolLayer, QgsProject, QgsVectorLayer, QgsField

from qaequilibrae.modules.common_tools import layer_from_dataframe

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_isochrones.ui"))


class IsochronesDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.setupUi(self)

        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.qgis_project = qgis_project
        self.all_modes = {}
        self.layer = None

        # Graph config
        with self.project.db_connection as conn:
            res = conn.execute("""select mode_name, mode_id from modes""")
            for x in res.fetchall():
                self.cob_modes.addItem(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        # TODO: Use numeric fields. Eg.: if we have joined fields from a result table
        #       it should appear here too.
        # Skim fields
        self.skimmeable_fields = self.project.network.skimmable_fields()
        for skim in self.skimmeable_fields:
            self.cob_minimizing.addItem(skim)
            self.cob_skim.addItem(skim)

        # Layer fields
        default_style = QgsStyle().defaultStyle()
        self.cob_color.addItems(list(default_style.colorRampNames()))

        self.cob_layer.addItems(["zones", "centroids", "nodes"])

        if self.layer:
            self.layer.selectionChanged.connect(self.select_after)

        self.but_plot.clicked.connect(self.run)

    def exit_procedure(self):
        self.close()

    def compute_skims(self):
        self.project.network.build_graphs()

        mode = self.all_modes[self.cob_modes.currentText()]
        graph = self.project.network.graphs[mode]

        # We prepare the graph to set all nodes as centroids
        if self.rdo_all_nodes.isChecked():
            graph.prepare_graph(graph.all_nodes)

        graph.set_graph(cost_field=self.cob_minimizing.currentText())
        graph.set_blocked_centroid_flows(self.block_paths.isChecked())

        graph.set_skimming(self.cob_skim.currentText())

        result = SkimResults()
        result.prepare(graph)

        skm = NetworkSkimming(graph, result)
        skm.execute()

        self.data_to_show = skm.results.skims.matrix[self.cob_skim.currentText()]
        self.indices = skm.results.skims.index.astype(np.int32)
        self.positional_dict = dict(zip(self.indices, np.arange(len(self.indices))))

    def plot_isochrone(self):
        lyr = "zones" if self.cob_layer.currentText() == "zones" else "nodes"
        self.layer = self.qgis_project.layers[lyr][0]
        self.layer_col = "zone_id" if lyr == "zones" else "node_id"
        QgsProject.instance().addMapLayer(self.layer)

    def map_ranges(self, fld, layer, color_ramp_name):
        from qaequilibrae.modules.gis.color_ramp_shades import color_ramp_shades

        # First, we check if we have numeric values in our column
        all_values = []
        for _, f in enumerate(layer.getFeatures()):
            all_values.append(f["isochrones_data"])

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
        color_ramp = color_ramp_shades(color_ramp_name, num_steps)

        # Create Rule-Based renderer
        root_rule = QgsRuleBasedRenderer.Rule(None)

        # Rule 1: NaN values
        hatch_symbol = self.create_hatch(layer, color_ramp[0])
        nan_expression = f'"{fld}" IS NULL OR "{fld}" = \'nan\' OR "{fld}" = \'NaN\''
        nan_rule = QgsRuleBasedRenderer.Rule(hatch_symbol, filterExp=nan_expression, label="NaN Values")
        root_rule.appendChild(nan_rule)

        # Rule 2: Inf values
        hatch_symbol = self.create_hatch(layer, color_ramp[0])
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
        lien.setPrefix("isochrones_")
        base_layer.addJoin(lien)

    def remove_mapping_layer(self, clear_selection=True):
        self.remove_data_layer()
        for lien in self.layer.vectorJoins():
            self.layer.removeJoin(lien.joinLayerId())
        self.mapping_layer = None
        if clear_selection:
            self.layer.selectByExpression(f'"{self.layer_col}"-<1000', QgsVectorLayer.SetSelection)
        self.layer.triggerRepaint()

    def remove_data_layer(self):
        active_layers = [name.name() for name in QgsProject.instance().mapLayers().values()]
        if "isochrones" in active_layers:
            layer = QgsProject.instance().mapLayersByName("isochrones")[0]
            QgsProject.instance().removeMapLayers([layer.id()])
            self.iface.mapCanvas().refresh()

            self.mapping_layer = None

    def map_dt(self, dt):
        self.remove_mapping_layer(False)
        df = pd.DataFrame({self.layer_col: self.indices, "data": dt})
        self.mapping_layer = layer_from_dataframe(df, "isochrones")
        self.make_join(self.layer, self.layer_col, self.mapping_layer)

        color_ramp_name = self.cob_color.currentText()
        self.map_ranges("isochrones_data", self.layer, color_ramp_name)

    def select_first(self):
        idx = int(self.line_start_id.text())
        dt = np.array(self.data_to_show[self.positional_dict[idx], :]).reshape(self.indices.shape[0])

        self.map_dt(dt)

    def select_after(self):
        selected_features = self.layer.selectedFeatures()
        idx = [feature[self.layer_col] for feature in selected_features][0]
        dt = np.array(self.data_to_show[self.positional_dict[idx], :]).reshape(self.indices.shape[0])
        self.map_dt(dt)

    def run(self):
        self.compute_skims()
        self.plot_isochrone()

        self.layer.selectionChanged.connect(self.select_after)

        self.select_first()

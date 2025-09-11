import logging
from math import ceil
from os.path import dirname, join
from pathlib import Path
from typing import Optional

import numpy as np
import openmatrix as omx
import pandas as pd
from aequilibrae.matrix import AequilibraeMatrix
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QComboBox, QCheckBox, QSpinBox, QLabel, QSpacerItem, QRadioButton
from qgis.PyQt.QtWidgets import QHBoxLayout, QTableView, QPushButton, QVBoxLayout, QAbstractItemView
from qgis.core import QgsProject, QgsStyle, QgsRuleBasedRenderer, Qgis
from qgis.core import QgsVectorLayer, QgsVectorLayerJoinInfo, QgsSymbol, QgsLinePatternFillSymbolLayer

from qaequilibrae.modules.common_tools import NumpyModel, GetOutputFileName
from qaequilibrae.modules.common_tools import layer_from_dataframe
from qaequilibrae.modules.common_tools.auxiliary_functions import standard_path

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_data_viewer.ui"))


class DisplayAequilibraEFormatsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project, file_path: Optional[Path] = None):
        QtWidgets.QDialog.__init__(self)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        qgis_project.block_change_scenario()
        self.finished.connect(qgis_project.allow_change_scenario)

        try:
            self.iface = qgis_project.iface
            self.setupUi(self)
            self.data_to_show = None
            self.error = None
            self.logger = logging.getLogger("AequilibraEGUI")
            self.qgis_project = qgis_project
            self.from_proj = True if qgis_project.project else False
            self.indices = np.array(1)
            self.mapping_layer = None
            self.selected_col = None
            self.selected_row = None
            self.zones_layer = None

            if isinstance(file_path, Path):
                self.data_path = file_path
                self.data_type = file_path.suffix.upper().split(".")[1]
                self.continue_with_data()
                return

            self.data_path, self.data_type = self.get_file_name()

            if not self.data_path or not self.data_type:
                self.error = self.tr("Path provided is not a valid dataset")
                self.exit_with_error()
            else:
                self.continue_with_data()

            if self.error:
                self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, True)
                self.but_load.clicked.connect(self.get_file_name)

            self.remove_data_layer()

        except Exception as e:
            qgis_project.allow_change_scenario()
            raise e

    def continue_with_data(self):
        self.setWindowTitle(self.tr("File path: {}").format(self.data_path))

        if self.data_type == "AEM":
            msg = "Support for AEM will be removed in a future version"
            self.qgis_project.message_log(msg, Qgis.MessageLevel.Warning, True)
            self.data_to_show = AequilibraeMatrix()
            if not self.from_proj:
                self.qgis_project.matrices[self.data_path] = self.data_to_show
            try:
                self.data_to_show.load(self.data_path)
                self.list_cores = self.data_to_show.names
                self.list_indices = self.data_to_show.index_names
            except Exception as e:
                self.error = self.tr("Could not load dataset")
                self.logger.error(e.args)
                self.exit_with_error()

        elif self.data_type == "OMX":
            with omx.open_file(self.data_path) as omx_file:
                if not self.from_proj:
                    self.qgis_project.matrices[self.data_path] = omx_file
                self.list_cores = omx_file.list_matrices()
                self.list_indices = omx_file.list_mappings()
                self.data_to_show = AequilibraeMatrix()

        # differentiates between AEM AND OMX
        if self.data_type == "AEM":
            self.data_to_show.computational_view([self.data_to_show.names[0]])
        elif self.data_type == "OMX":
            self.add_matrix_parameters(self.list_indices[0], self.list_cores[0])

        # Elements that will be used during the displaying
        self._layout = QVBoxLayout()
        self.table = QTableView()
        self._layout.addWidget(self.table)

        # Settings for displaying
        self.show_layout = QHBoxLayout()

        # Thousand separator
        self.thousand_separator = QCheckBox()
        self.thousand_separator.setChecked(True)
        self.thousand_separator.setText(self.tr("Thousands separator"))
        self.thousand_separator.toggled.connect(self.format_showing)
        self.show_layout.addWidget(self.thousand_separator)

        self.spacer = QSpacerItem(5, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.show_layout.addItem(self.spacer)

        # Decimals
        txt = QLabel()
        txt.setText(self.tr("Decimal places"))
        self.show_layout.addWidget(txt)
        self.decimals = QSpinBox()
        self.decimals.valueChanged.connect(self.format_showing)
        self.decimals.setMinimum(0)
        self.decimals.setValue(4)
        self.decimals.setMaximum(10)

        self.show_layout.addWidget(self.decimals)
        self._layout.addItem(self.show_layout)

        # Matrices need cores and indices to be set as well
        self.mat_layout = QHBoxLayout()
        self.mat_list = QComboBox()

        for n in self.list_cores:
            self.mat_list.addItem(n)

        self.mat_list.currentIndexChanged.connect(self.change_matrix_cores)
        self.mat_layout.addWidget(self.mat_list)

        self.idx_list = QComboBox()
        for i in self.list_indices:
            self.idx_list.addItem(i)

        self.idx_list.currentIndexChanged.connect(self.change_matrix_cores)
        self.mat_layout.addWidget(self.idx_list)
        self._layout.addItem(self.mat_layout)
        self.change_matrix_cores()

        if self.from_proj:
            default_style = QgsStyle().defaultStyle()
            self.mapping_layout = QHBoxLayout()

            self.no_mapping = QRadioButton()
            self.no_mapping.setText(self.tr("No mapping"))
            self.no_mapping.toggled.connect(self.set_mapping)

            self.by_row = QRadioButton()
            self.by_row.setText(self.tr("By origin"))
            self.by_row.toggled.connect(self.set_mapping)

            self.by_col = QRadioButton()
            self.by_col.setText(self.tr("By destination"))
            self.by_col.toggled.connect(self.set_mapping)

            self.cob_colors = QComboBox()
            self.cob_colors.addItems(list(default_style.colorRampNames()))

            self.no_mapping.setChecked(True)

            self.mapping_layout.addWidget(self.no_mapping)
            self.mapping_layout.addWidget(self.by_row)
            self.mapping_layout.addWidget(self.by_col)
            self.mapping_layout.addWidget(self.cob_colors)
            self._layout.addItem(self.mapping_layout)

            if self.zones_layer:
                self.zones_layer.selectionChanged.connect(self.select_from_layer)

        self.but_export = QPushButton()
        self.but_export.setText(self.tr("Export"))
        self.but_export.clicked.connect(self.export)

        self.but_close = QPushButton()
        self.but_close.setText(self.tr("Close"))
        self.but_close.clicked.connect(self.exit_procedure)

        self.but_layout = QHBoxLayout()
        self.but_layout.addWidget(self.but_export)
        self.but_layout.addWidget(self.but_close)

        self._layout.addItem(self.but_layout)

        self.resize(700, 500)
        self.setLayout(self._layout)
        self.format_showing()

    def select_from_layer(self):
        selected_features = self.zones_layer.selectedFeatures()
        if selected_features:
            idx = [feature["zone_id"] for feature in selected_features][0]
            if self.by_row.isChecked():
                self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
                self.table.selectRow(self.idx_mapping[idx])
            elif self.by_col.isChecked():
                self.table.setSelectionBehavior(QAbstractItemView.SelectColumns)
                self.table.selectColumn(self.idx_mapping[idx])

    def select_column(self):
        self.selected_col = None
        col_id = [col_idx.column() for col_idx in self.table.selectionModel().selectedColumns()]
        if not col_id:
            return
        self.selected_col = col_id[0]

        self.zones_layer.blockSignals(True)
        self.zones_layer.selectByExpression(f'"zone_id"={self.indices[col_id[0]]}', QgsVectorLayer.SetSelection)
        self.zones_layer.blockSignals(False)
        self.iface.mapCanvas().refresh()

        core = self.mat_list.currentText()
        dt = np.array(self.data_to_show.matrix[core][:, col_id]).reshape(self.indices.shape[0])

        self.map_dt(dt)

    def select_row(self):
        self.selected_row = None
        row_id = [rowidx.row() for rowidx in self.table.selectionModel().selectedRows()]
        if not row_id:
            return
        self.selected_row = row_id[0]

        self.zones_layer.blockSignals(True)
        self.zones_layer.selectByExpression(f'"zone_id"={self.indices[row_id[0]]}', QgsVectorLayer.SetSelection)
        self.zones_layer.blockSignals(False)

        core = self.mat_list.currentText()
        dt = np.array(self.data_to_show.matrix[core][row_id[0], :]).reshape(self.indices.shape[0])

        self.map_dt(dt)

    def map_dt(self, dt):
        self.remove_mapping_layer(False)
        df = pd.DataFrame({"zone_id": self.indices, "data": dt})
        self.mapping_layer = layer_from_dataframe(df, "visualize_data")
        self.make_join(self.zones_layer, "zone_id", self.mapping_layer)
        self.draw_zone_styles()

        self.iface.setActiveLayer(self.zones_layer)

    def make_join(self, base_layer, join_field, metric_layer):
        lien = QgsVectorLayerJoinInfo()
        lien.setJoinFieldName(join_field)
        lien.setTargetFieldName(join_field)
        lien.setJoinLayerId(metric_layer.id())
        lien.setUsingMemoryCache(True)
        lien.setJoinLayer(metric_layer)
        lien.setPrefix("matrix_")
        base_layer.addJoin(lien)

    def draw_zone_styles(self):
        color_ramp_name = self.cob_colors.currentText()

        self.map_ranges("matrix_data", self.zones_layer, color_ramp_name)

    def map_ranges(self, fld, layer, color_ramp_name):
        from qaequilibrae.modules.gis.color_ramp_shades import color_ramp_shades

        # First, we check if we have numeric values in our column
        all_values = []
        for _, f in enumerate(layer.getFeatures()):
            all_values.append(f["matrix_data"])

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
        color_ramp = color_ramp_shades(color_ramp_name, num_steps, False)

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

    def set_mapping(self):
        self.table.clearSelection()
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        if not self.from_proj:
            return

        if self.from_proj:
            self.zones_layer = self.qgis_project.layers["zones"][0]
            QgsProject.instance().addMapLayer(self.zones_layer)

        self.remove_mapping_layer()
        if self.no_mapping.isChecked():
            return

        if self.by_row.isChecked():
            self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.selected_col = None
            if self.selected_row:
                self.table.blockSignals(True)
                self.table.selectRow(self.selected_row)
                self.table.blockSignals(False)
                self.select_row()
            self.table.selectionModel().selectionChanged.connect(self.select_row)
        elif self.by_col.isChecked():
            self.table.setSelectionBehavior(QAbstractItemView.SelectColumns)
            self.selected_row = None
            if self.selected_col:
                self.table.blockSignals(True)
                self.table.selectColumn(self.selected_col)
                self.table.blockSignals(False)
                self.select_column()
            self.table.selectionModel().selectionChanged.connect(self.select_column)

    def remove_mapping_layer(self, clear_selection=True):
        self.remove_data_layer()
        for lien in self.zones_layer.vectorJoins():
            self.zones_layer.removeJoin(lien.joinLayerId())
        self.mapping_layer = None
        if clear_selection:
            self.zones_layer.selectByExpression('"zone_id"-<1000', QgsVectorLayer.SetSelection)
        self.zones_layer.triggerRepaint()

    def format_showing(self):
        if self.data_to_show is None:
            return
        decimals = self.decimals.value()
        separator = self.thousand_separator.isChecked()
        m = NumpyModel(self.data_to_show, separator, decimals)
        self.table.clearSpans()
        self.table.setModel(m)

    def change_matrix_cores(self):
        idx = self.idx_list.currentText()
        core = self.mat_list.currentText()
        if self.data_type == "AEM":
            self.data_to_show.computational_view([core])
            self.data_to_show.set_index(idx)
            self.format_showing()
        elif self.data_type == "OMX":
            self.add_matrix_parameters(idx, core)
            self.format_showing()

        self.indices = self.data_to_show.index.astype(np.int32)
        self.idx_mapping = dict(zip(self.indices, np.arange(self.indices.shape[0])))

    def csv_file_path(self):
        new_name, _ = GetOutputFileName(
            self, "Export matrix data", ["Comma-separated file(*.csv)"], ".csv", self.data_path
        )
        return new_name

    def export(self):
        new_name = self.csv_file_path()

        if new_name is not None:
            self.data_to_show.export(new_name)

    def exit_with_error(self):
        self.qgis_project.iface_error_message(self.error)
        self.close()

    def exit_procedure(self):
        if not self.from_proj:
            self.qgis_project.matrices.pop(self.data_path)
        self.show()
        self.close()

    def add_matrix_parameters(self, idx, field):
        with omx.open_file(self.data_path, "a") as omx_file:
            matrix_name = self.data_to_show.random_name()
            matrix_index = np.array(list(omx_file.mapping(idx).keys()))

            args = {
                "zones": matrix_index.shape[0],
                "matrix_names": [field],
                "file_name": matrix_name,
                "memory_only": True,
            }

            self.data_to_show.create_empty(**args)
            self.data_to_show.matrix_view = np.array(omx_file[field])
            self.data_to_show.index = np.array(list(omx_file.mapping(idx).keys()))
            self.data_to_show.matrix[field] = self.data_to_show.matrix_view[:, :]

    def get_file_name(self):
        formats = ["AequilibraE Matrix (*.aem)", "OpenMatrix (*.omx)"]
        dflt = ".omx"

        data_path, data_type = GetOutputFileName(
            self,
            self.tr("AequilibraE custom formats"),
            formats,
            dflt,
            standard_path(),
        )

        return data_path, data_type

    def remove_data_layer(self):
        active_layers = [name.name() for name in QgsProject.instance().mapLayers().values()]
        if "visualize_data" in active_layers:
            layer = QgsProject.instance().mapLayersByName("visualize_data")[0]
            QgsProject.instance().removeMapLayers([layer.id()])
            self.iface.mapCanvas().refresh()

            self.mapping_layer = None

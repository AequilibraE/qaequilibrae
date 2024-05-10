import logging
import os
import openmatrix as omx
import numpy as np
import pandas as pd
from math import ceil
from aequilibrae.matrix import AequilibraeMatrix, AequilibraeData

import qgis
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtWidgets import QComboBox, QCheckBox, QSpinBox, QLabel, QSpacerItem
from qgis.PyQt.QtWidgets import QHBoxLayout, QTableView, QPushButton, QVBoxLayout
from qgis.PyQt.QtWidgets import QRadioButton, QAbstractItemView
from qgis._core import QgsVectorLayer, QgsVectorLayerJoinInfo, QgsSymbol, QgsApplication
from qgis._core import QgsRendererRange, QgsGraduatedSymbolRenderer, QgsProject, QgsStyle
from qaequilibrae.modules.common_tools import DatabaseModel, NumpyModel, GetOutputFileName
from qaequilibrae.modules.common_tools import layer_from_dataframe
from qaequilibrae.modules.common_tools.auxiliary_functions import standard_path

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_data_viewer.ui"))


class DisplayAequilibraEFormatsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project, file_path="", proj=False):
        QtWidgets.QDialog.__init__(self)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        self.iface = qgis_project.iface
        self.setupUi(self)
        self.data_to_show = None
        self.error = None
        self.logger = logging.getLogger("AequilibraEGUI")
        self.qgis_project = qgis_project
        self.from_proj = proj
        self.indices = np.array(1)
        self.mapping_layer = None
        self.selected_col = None
        self.selected_row = None

        self.__remove_temp_tables()

        if len(file_path) > 0:
            self.data_path = file_path
            self.data_type = self.data_path[-3:].upper()
            self.continue_with_data()
            return

        self.data_path, self.data_type = self.get_file_name()

        if self.data_type is None:
            self.error = self.tr("Path provided is not a valid dataset")
            self.exit_with_error()
        else:
            self.data_type = self.data_type.upper()
            self.continue_with_data()
        
        if self.error:
            self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, True)
            self.but_load.clicked.connect(self.get_file_name)

    def continue_with_data(self):
        self.setWindowTitle(self.tr("File path: {}").format(self.data_path))

        if self.data_type in ["AED", "AEM"]:
            if self.data_type == "AED":
                self.data_to_show = AequilibraeData()
            elif self.data_type == "AEM":
                self.data_to_show = AequilibraeMatrix() 
            if not self.from_proj:
                self.qgis_project.matrices[self.data_path] = self.data_to_show
            try:
                self.data_to_show.load(self.data_path)
                if self.data_type == "AED":
                    self.list_cores = self.data_to_show.fields
                elif self.data_type == "AEM":
                    self.list_cores = self.data_to_show.names
                    self.list_indices = self.data_to_show.index_names
            except Exception as e:
                self.error = self.tr("Could not load dataset")
                self.logger.error(e.args)
                self.exit_with_error()

        elif self.data_type == "OMX":
            self.omx = omx.open_file(self.data_path, "r")
            if not self.from_proj:
                self.qgis_project.matrices[self.data_path] = self.omx
            self.list_cores = self.omx.list_matrices()
            self.list_indices = self.omx.list_mappings()
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

        # differentiates between matrix and dataset
        if self.data_type in ["AEM", "OMX"]:
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
            self.no_mapping.setText("No mapping")
            self.no_mapping.toggled.connect(self.set_mapping)

            self.by_row = QRadioButton()
            self.by_row.setText("By origin")
            self.by_row.toggled.connect(self.set_mapping)

            self.by_col = QRadioButton()
            self.by_col.setText("By destination")
            self.by_col.toggled.connect(self.set_mapping)

            self.cob_colors = QComboBox()
            self.cob_colors.addItems(list(default_style.colorRampNames()))

            self.no_mapping.setChecked(True)

            self.mapping_layout.addWidget(self.no_mapping)
            self.mapping_layout.addWidget(self.by_row)
            self.mapping_layout.addWidget(self.by_col)
            self.mapping_layout.addWidget(self.cob_colors)
            self._layout.addItem(self.mapping_layout)

        self.but_export = QPushButton()
        self.but_export.setText(self.tr("Export"))
        self.but_export.clicked.connect(self.export)

        self.but_close = QPushButton()
        self.but_close.clicked.connect(self.exit_procedure)
        self.but_close.setText(self.tr("Close"))

        self.but_layout = QHBoxLayout()
        self.but_layout.addWidget(self.but_export)
        self.but_layout.addWidget(self.but_close)

        self._layout.addItem(self.but_layout)

        self.resize(700, 500)
        self.setLayout(self._layout)
        self.format_showing()

    def select_column(self):
        self.selected_col = None
        col_id = [col_idx.column() for col_idx in self.table.selectionModel().selectedColumns()]
        if not col_id:
            return
        self.selected_col = col_id[0]
        self.zones_layer.selectByExpression(f'"zone_id"={self.indices[col_id[0]]}', QgsVectorLayer.SetSelection)
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
        self.zones_layer.selectByExpression(f'"zone_id"={self.indices[row_id[0]]}', QgsVectorLayer.SetSelection)

        core = self.mat_list.currentText()
        dt = np.array(self.data_to_show.matrix[core][row_id[0], :]).reshape(self.indices.shape[0])
        
        self.map_dt(dt)

    def map_dt(self, dt):
        self.remove_mapping_layer(False)
        df = pd.DataFrame({"zone_id": self.indices, "data": dt}).dropna()
        self.mapping_layer = layer_from_dataframe(df, "matrix_row")
        self.qgis_project.layers["matrix_row"] = [self.mapping_layer, self.mapping_layer.id()]
        self.make_join(self.zones_layer, "zone_id", self.mapping_layer)
        self.draw_zone_styles()

    def make_join(self, base_layer, join_field, metric_layer):
        lien = QgsVectorLayerJoinInfo()
        lien.setJoinFieldName(join_field)
        lien.setTargetFieldName(join_field)
        lien.setJoinLayerId(metric_layer.id())
        lien.setUsingMemoryCache(True)
        lien.setJoinLayer(metric_layer)
        lien.setPrefix("metrics_")
        base_layer.addJoin(lien)

    def draw_zone_styles(self):
        color_ramp_name = self.cob_colors.currentText()

        self.map_ranges("metrics_data", self.zones_layer, color_ramp_name)

    def map_ranges(self, fld, layer, color_ramp_name):
        from qaequilibrae.modules.gis.color_ramp_shades import color_ramp_shades
    
        idx = self.zones_layer.fields().indexFromName("metrics_data")
        max_metric = self.zones_layer.maximumValue(idx)

        num_steps = 9
        max_metric = num_steps if max_metric is None else max_metric
        values = [ceil(i * (max_metric / num_steps)) for i in range(1, num_steps + 1)]
        values = [0, 0.000001] + values
        color_ramp = color_ramp_shades(color_ramp_name, num_steps)
        ranges = []
        for i in range(num_steps + 1):
            myColour = color_ramp[i]
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(myColour)
            symbol.setOpacity(1)

            if i == 0:
                label = f"0/Null ({fld.replace('metrics_', '')})"
            elif i == 1:
                label = f"Up to {values[i + 1]:,.0f}"
            else:
                label = f"{values[i]:,.0f} to {values[i + 1]:,.0f}"

            ranges.append(QgsRendererRange(values[i], values[i + 1], symbol, label))

        sizes = [0, max_metric]
        renderer = QgsGraduatedSymbolRenderer("", ranges)
        renderer.setSymbolSizes(*sizes)
        renderer.setClassAttribute(f"""coalesce("{fld}", 0)""")

        classific_method = QgsApplication.classificationMethodRegistry().method("EqualInterval")
        renderer.setClassificationMethod(classific_method)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
        self.iface.mapCanvas().setExtent(layer.extent())
        self.iface.mapCanvas().refresh()

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
            self.table.setSelectionMode(QAbstractItemView.SingleSelection)
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
        if self.mapping_layer is not None:
            QgsProject.instance().removeMapLayers([self.mapping_layer.id()])
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
        if isinstance(self.data_to_show, AequilibraeMatrix):
            m = NumpyModel(self.data_to_show, separator, decimals)
        else:
            m = DatabaseModel(self.data_to_show, separator, decimals)
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

    def csv_file_path(self):
        new_name, _ = GetOutputFileName(
            self, self.data_type, ["Comma-separated file(*.csv)"], ".csv", self.data_path
        )
        return new_name

    def export(self):
        new_name = self.csv_file_path()

        if new_name is not None:
            self.data_to_show.export(new_name)

    def exit_with_error(self):
        qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1, duration=10)
        self.close()

    def exit_procedure(self):
        if not self.from_proj:
            self.qgis_project.matrices.pop(self.data_path)
        self.show()
        self.close()

    def add_matrix_parameters(self, idx, field):
        matrix_name = self.data_to_show.random_name()
        matrix_index = np.array(list(self.omx.mapping(idx).keys()))

        args = {"zones": matrix_index.shape[0], "matrix_names": [field], "file_name": matrix_name, "memory_only": True}

        self.data_to_show.create_empty(**args)
        self.data_to_show.matrix_view = np.array(self.omx[field])
        self.data_to_show.index = np.array(list(self.omx.mapping(idx).keys()))
        self.data_to_show.matrix[field] = self.data_to_show.matrix_view[:, :]

    def get_file_name(self):
        formats = ["Aequilibrae matrix(*.aem)", "Aequilibrae dataset(*.aed)", "OpenMatrix(*.omx)"]
        dflt = ".aem"

        data_path, data_type = GetOutputFileName(
            self,
            self.tr("AequilibraE custom formats"),
            formats,
            dflt,
            standard_path(),
        )

        return data_path, data_type

    def __remove_temp_tables(self):
        for layer, values in self.qgis_project.layers.items():
            if layer == "matrix_row":
                QgsProject.instance().removeMapLayers([values[1]])

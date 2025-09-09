import sys
from os.path import dirname, join

import pandas as pd
import qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QComboBox, QCheckBox, QTableWidgetItem
from qgis.core import QgsMapLayerProxyModel

from qaequilibrae.modules.common_tools import standard_path, BaseDialog
from qaequilibrae.modules.project_procedures.add_zones_procedure import AddZonesProcedure

sys.modules["qgsmaplayercombobox"] = qgis.gui


class AddZonesDialog(BaseDialog):
    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_add_zoning.ui"), qgis_project=qgis_project)

    def _base_ui_setup(self):
        self.path = standard_path()
        self.cob_lyr.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        self.but_run.clicked.connect(self.run)
        self.cob_lyr.currentIndexChanged.connect(self.changed_layer)
        self.changed_layer()

        self.progress_box.setVisible(False)

    def run(self):
        if self.cob_lyr.currentIndex() == -1:
            return
        layer = self.cob_lyr.currentLayer()
        field_correspondence = {}

        for row in range(self.table_fields.rowCount()):
            f = self.table_fields.item(row, 1).text()
            if not self.table_fields.cellWidget(row, 0).findChildren(QCheckBox)[0].isChecked():
                continue
            widget = self.table_fields.cellWidget(row, 2).findChildren(QComboBox)[0]
            source_name = widget.currentText()
            val = layer.dataProvider().fieldNameIndex(source_name)
            field_correspondence[f] = val

        self.setFixedHeight(65)
        self.progress_box.setVisible(True)
        self.input_box.setVisible(False)
        self.worker_thread = AddZonesProcedure(
            qgis.utils.iface.mainWindow(),
            self.project,
            layer,
            self.chb_select.isChecked(),
            self.chb_add_centroids.isChecked(),
            field_correspondence,
        )

        self.worker_thread.signal.connect(self.signal_handler)
        self.worker_thread.start()
        self.show()

    def changed_layer(self):
        with self.project.db_connection as conn:
            if not self.project or not conn:
                return
            ignore_fields = ["ogc_fid", "geometry"]
            not_initializable = ["zone_id"]

            fields = pd.read_sql("PRAGMA table_info(zones)", conn).name.to_list()
            fields = [x.lower() for x in fields if x not in ignore_fields]

            self.table_fields.clearContents()
            self.table_fields.setRowCount(len(fields))

            layer_fields = self.cob_lyr.currentLayer().fields() if self.cob_lyr.currentLayer() else []

            for counter, field in enumerate(fields):
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table_fields.setItem(counter, 1, item1)

                chb1 = QCheckBox()
                chb1.setChecked(True)
                if field in not_initializable:
                    chb1.setEnabled(False)
                self.table_fields.setCellWidget(counter, 0, self.centers_item(chb1))

                cbb = QComboBox()
                for i in layer_fields:
                    cbb.addItem(i.name())
                self.table_fields.setCellWidget(counter, 2, self.centers_item(cbb))

    def centers_item(self, item):
        cell_widget = QWidget()
        lay_out = QHBoxLayout(cell_widget)
        lay_out.addWidget(item)
        lay_out.setAlignment(Qt.AlignCenter)
        lay_out.setContentsMargins(0, 0, 0, 0)
        cell_widget.setLayout(lay_out)
        return cell_widget

    def signal_handler(self, val):
        if val[0] == "start":
            self.progress_label.setText(val[2])
            self.progressbar.setValue(0)
            self.progressbar.setMaximum(val[1])
        elif val[0] == "update":
            self.progressbar.setValue(val[1])
        elif val[0] == "finished":
            self.exit_procedure()

    def exit_procedure(self):
        self.close()

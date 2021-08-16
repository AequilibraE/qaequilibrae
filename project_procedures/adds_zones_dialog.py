import qgis
from qgis.core import *
import sys
import os
from os.path import isdir, join
import pandas as pd
from qgis.PyQt.QtCore import *
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QWidget, QFileDialog, QHBoxLayout
from functools import partial
from ..common_tools.global_parameters import *
from ..common_tools.get_output_file_name import GetOutputFileName
from ..common_tools.all_layers_from_toc import all_layers_from_toc
from ..common_tools.auxiliary_functions import *
from ..common_tools import ReportDialog
from .creates_transponet_procedure import CreatesTranspoNetProcedure
from aequilibrae.project.network.network import Network
from aequilibrae import Parameters

sys.modules["qgsmaplayercombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_add_zoning.ui"))


class AddZonesDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgisproject):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgisproject.iface
        self.project = qgisproject.project
        self.setupUi(self)

        self.path = standard_path()
        self.cob_lyr.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        self.but_run.clicked.connect(self.run)
        self.cob_lyr.currentIndexChanged.connect(self.changed_layer)
        self.changed_layer()

    def run(self):
        pass

    def changed_layer(self):

        ignore_fields = ['ogc_fid', 'geometry']
        not_initializable = ['zone_id']

        fields = pd.read_sql('PRAGMA table_info(zones)', self.project.conn).name.to_list()
        fields = [x.lower() for x in fields if x not in ignore_fields]

        self.table_fields.clearContents()
        self.table_fields.setRowCount(len(fields))

        layer_fields = self.cob_lyr.currentLayer().fields() if self.cob_lyr.currentLayer() else []

        for counter, field in enumerate(fields):
            item1 = QtWidgets.QTableWidgetItem(field)
            item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table_fields.setItem(counter, 1, item1)

            chb1 = QtWidgets.QCheckBox()
            chb1.setChecked(True)
            if field in not_initializable:
                chb1.setEnabled(False)
            self.table_fields.setCellWidget(counter, 0, self.centers_item(chb1))

            cbb = QtWidgets.QComboBox()
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

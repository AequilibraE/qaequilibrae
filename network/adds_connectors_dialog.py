import os
import sys

import qgis
from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsMapLayerProxyModel
from .adds_connectors_procedure import AddsConnectorsProcedure

sys.modules["qgsmaplayercombobox"] = qgis.gui
sys.modules["qgsfieldcombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "./forms/ui_add_connectors.ui"))


class AddConnectorsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)

        self.NewLinks = False
        self.NewNodes = False
        self.qgis_project = qgis_project
        self.project = qgis_project.project
        self.conn = self.project.conn
        self.path_to_file = self.project.path_to_file

        modes = self.project.network.modes.all_modes()
        link_types = self.project.network.link_types.all_types()

        self.modes = {m.mode_name: mode_id for mode_id, m in modes.items()}
        self.link_types = {lt.link_type: lt_id for lt_id, lt in link_types.items()}

        self.lst_modes.addItems(sorted(list(self.modes.keys())))
        self.lst_link_types.addItems(sorted(list(self.link_types.keys())))

        self.lst_modes.setSelectionMode(qgis.PyQt.QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lst_link_types.setSelectionMode(qgis.PyQt.QtWidgets.QAbstractItemView.ExtendedSelection)

        self.rdo_network.toggled.connect(self.centroid_source)
        self.rdo_zone.toggled.connect(self.centroid_source)
        self.rdo_layer.toggled.connect(self.centroid_source)

        self.layer_box.layerChanged.connect(self.set_fields)
        self.layer_box.setFilters(QgsMapLayerProxyModel.PointLayer)

        self.but_process.clicked.connect(self.run)

    def centroid_source(self):
        self.layer_box.setEnabled(self.rdo_layer.isChecked())
        self.field_box.setEnabled(self.rdo_layer.isChecked())
        self.field_box.setVisible(not self.rdo_zone.isChecked())
        self.lbl_radius.setVisible(not self.rdo_zone.isChecked())

    def set_fields(self):
        self.field_box.setLayer(self.layer_box.currentLayer())

    def run(self):
        source = "network" if self.rdo_network.isChecked() else "zone"
        source = "layer" if self.rdo_layer.isChecked() else source

        num_connectors = self.connectors.value()

        link_types = [item.text() for item in self.lst_link_types.selectedItems()]
        link_types = "".join([self.link_types[lt] for lt in link_types])

        modes = [item.text() for item in self.lst_modes.selectedItems()]
        modes = [self.modes[md] for md in modes]

        parameters = {
            "qgis_project": self.qgis_project,
            "link_types": link_types,
            "modes": modes,
            "num_connectors": num_connectors,
            "source": source,
        }

        if source != "zone":
            parameters["radius"] = self.sb_radius.value()
        if source == "layer":
            parameters["layer"] = self.layer_box.currentLayer()
            parameters["field"] = self.field_box.currentField()
        self.worker_thread = AddsConnectorsProcedure(qgis.utils.iface.mainWindow(), **parameters)
        self.run_thread()

    def run_thread(self):
        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressText.connect(self.progress_text_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.jobFinished.connect(self.job_finished_from_thread)
        self.worker_thread.start()
        self.show()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value)

    def job_finished_from_thread(self, success):
        self.but_process.setEnabled(True)
        self.project.network.refresh_connection()
        self.project.network.links.refresh_connection()
        self.project.network.nodes.refresh_connection()
        self.project.zoning.refresh_connection()
        self.exit_procedure()

    def exit_procedure(self):
        self.close()

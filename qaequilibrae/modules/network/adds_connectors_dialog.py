import sys
from os.path import dirname, join

import qgis
from qgis.core import QgsMapLayerProxyModel

from qaequilibrae.modules.common_tools import BaseDialog, ProgressBar
from qaequilibrae.modules.network.adds_connectors_procedure import AddsConnectorsProcedure

sys.modules["qgsmaplayercombobox"] = qgis.gui
sys.modules["qgsfieldcombobox"] = qgis.gui


class AddConnectorsDialog(BaseDialog):
    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_add_connectors.ui"), qgis_project=qgis_project)

    def _base_ui_setup(self):
        self.NewLinks = False
        self.NewNodes = False

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

        self.chb_zone.setVisible(False)

        self.but_process.clicked.connect(self.run)

    def centroid_source(self):
        self.layer_box.setEnabled(self.rdo_layer.isChecked())
        self.field_box.setEnabled(self.rdo_layer.isChecked())
        self.field_box.setVisible(not self.rdo_zone.isChecked())
        self.lbl_radius.setVisible(not self.rdo_zone.isChecked())
        self.sb_radius.setVisible(not self.rdo_zone.isChecked())
        self.layer_box.setVisible(not self.rdo_zone.isChecked())
        self.chb_zone.setVisible(self.rdo_zone.isChecked())

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

        if source == "zone":
            parameters["limit_to_zone"] = self.chb_zone.isChecked()
        else:
            parameters["radius"] = self.sb_radius.value()
        if source == "layer":
            parameters["layer"] = self.layer_box.currentLayer()
            parameters["field"] = self.field_box.currentField()

        self.worker_thread = AddsConnectorsProcedure(qgis.utils.iface.mainWindow(), **parameters)

        progress_bar = ProgressBar(self.qgis_project, self.worker_thread)
        _ = progress_bar.run()

        self.project.network.links.refresh()
        self.project.network.nodes.refresh()
        progress_bar.exit_procedure()

    def exit_procedure(self):
        self.close()

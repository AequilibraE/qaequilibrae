from os.path import dirname, join

from typing import Tuple

import pandas as pd
from qgis.PyQt import QtWidgets, uic, QtCore

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_load_network_info.ui"))


class LoadGraphLayerSettingDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project, modes: pd.DataFrame, min_fields: Tuple[str]):
        QtWidgets.QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        qgis_project.block_change_scenario()
        self.qgis_project = qgis_project
        self.project = qgis_project.project
        self.setupUi(self)
        self.minimize_field = ""
        self.mode = ""
        self.link_layer = ""
        self.node_layer = ""
        self.error = []
        self.all_modes = {}

        for _, rec in modes.iterrows():
            key = f"{rec.mode_name} ({rec.mode_id})"

            self.cb_modes.addItem(key)
            self.all_modes[key] = rec.mode_id

        dual_fields = []
        for f in min_fields:
            if f[-2:] == "ab":
                if f[:-2] + "ba" in min_fields:
                    dual_fields.append(f[:-3])
            elif f[-3:] != "_ba":
                dual_fields.append(f)

        self.cb_minimizing.addItems(sorted(dual_fields))

        self.do_load_graph.clicked.connect(self.exit_procedure)

        self.finished.connect(qgis_project.allow_change_scenario)

    def exit_procedure(self):
        self.mode = self.all_modes[self.cb_modes.currentText()]
        self.minimize_field = self.cb_minimizing.currentText()
        self.block_connector = self.block_paths.isChecked()
        self.remove_chosen_links = self.chb_chosen_links.isChecked()
        self.close()

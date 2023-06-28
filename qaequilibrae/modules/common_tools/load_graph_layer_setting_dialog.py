import logging
import os
from aequilibrae.paths import Graph
from aequilibrae.project import Project

from qgis.PyQt import QtWidgets, uic, QtCore

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_load_network_info.ui"))


class LoadGraphLayerSettingDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, project: Project):
        # QtWidgets.QDialog.__init__(self)
        QtWidgets.QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        self.iface = iface
        self.project = project
        self.setupUi(self)
        self.minimize_field = ""
        self.mode = ""
        self.link_layer = ""
        self.node_layer = ""
        self.error = []
        self.all_modes = {}

        curr = self.project.network.conn.cursor()
        curr.execute("""select mode_name, mode_id from modes""")

        for x in curr.fetchall():
            self.cb_modes.addItem(f"{x[0]} ({x[1]})")
            self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        for field in self.project.network.skimmable_fields():
            self.cb_minimizing.addItem(field)

        self.do_load_graph.clicked.connect(self.exit_procedure)

    def exit_procedure(self):
        self.mode = self.all_modes[self.cb_modes.currentText()]
        self.minimize_field = self.cb_minimizing.currentText()
        self.block_connector = self.block_paths.isChecked()
        self.remove_chosen_links = self.chb_chosen_links.isChecked()
        self.close()

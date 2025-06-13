import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QComboBox
from qgis.core import QgsStyle

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_isochrones.ui"))


class IsochronesDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)

        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.qgis_project = qgis_project

        # Graph config
        with self.project.db_connection as conn:
            res = conn.execute("""select mode_name, mode_id from modes""")
            for x in res.fetchall():
                self.cob_modes.addItem(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        # Skim fields
        self.skimmeable_fields = self.project.network.skimmable_fields()
        for skim in self.skimmeable_fields:
            self.cob_minimizing.addItem(skim)
            self.cob_skim.addItem(skim)

        # Layer fields
        self.cob_layer = QComboBox()
        self.cob_layer.addItems(["zones", "centroids", "nodes"])

        default_style = QgsStyle().defaultStyle()
        self.cob_colors = QComboBox()
        self.cob_colors.addItems(list(default_style.colorRampNames()))

    def exit_procedure(self):
        self.close()

    
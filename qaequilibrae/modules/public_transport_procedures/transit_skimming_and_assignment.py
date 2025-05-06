from os.path import join, dirname

from qgis.PyQt import uic, QtGui
from qgis.PyQt.QtWidgets import QDialog

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_skimming_assignment.ui"))


class TransitSkimAssign(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.setupUi(self)
        self.project = qgis_project.project

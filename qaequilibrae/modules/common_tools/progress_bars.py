from os.path import isdir, dirname, join
from pathlib import Path

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QGridLayout, QPushButton, QLineEdit, QComboBox, QLabel, QVBoxLayout
from qgis.PyQt.QtWidgets import QWidget, QFileDialog

from qaequilibrae.modules.common_tools import standard_path

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "../common_tools/forms/ui_progress_bar.ui"))


class ProgressBar(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)

    
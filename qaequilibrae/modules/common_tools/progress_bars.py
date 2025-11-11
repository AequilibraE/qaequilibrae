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
        qgis_project.block_change_scenario()  # We cannot change scenarios in the middle of an ongoing process
        self.setupUi(self)
        self.qgis_project = qgis_project

        self.finished.connect(qgis_project.allow_change_scenario)

    def signal_handler(self, val):
        # self.qgis_project.message_log(str(val))
        if val[0] == "finished":
            self.exit_procedure()
        elif val[0] == "refresh":
            pass
        elif val[0] == "reset":
            pass
        elif val[0] == "start":
            self.pbar_2.setValue(0)
            self.pbar_2.setMaximum(val[1])
            self.label_2.setText(val[2])
        elif val[0] == "set_position":
            pass
        elif val[0] == "set_text":
            pass
        elif val[0] == "update":
            self.pbar_2.setValue(val[1])
            self.label_2.setText(val[2])

    def exit_procedure(self):
        self.close()

from os.path import join, dirname

from aequilibrae.project import Project
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtWidgets import QTimeEdit, QLineEdit, QWidget
from qgis.PyQt.QtWidgets import QGridLayout, QPushButton, QComboBox, QLabel, QVBoxLayout

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class NewPeriodDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, project: Project):
        QtWidgets.QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        self.iface = iface
        self.project = project
        self.setupUi(self)
        self.error = []

        self._run_layout = QGridLayout()

        lbl = QLabel(self.tr("Add new period"))

        self.time_start = QTimeEdit()

        self.time_end = QTimeEdit()

        self.ln_period_desc = QLineEdit()

        self.but_run = QPushButton()
        self.but_run.setText(self.tr("Add"))
        self.but_run.clicked.connect(self.run)

        self.buttons_frame = QVBoxLayout()
        self.buttons_frame.addWidget(self.ln_period_desc)
        self.buttons_frame.addWidget(self.but_run)

        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_frame)

        self.update_widget = QWidget()
        self.update_frame = QVBoxLayout()
        self.update_widget.setLayout(self.update_frame)
        self.update_widget.setVisible(False)

        self._run_layout.addWidget(lbl)
        self._run_layout.addWidget(self.buttons_widget)
        self._run_layout.addWidget(self.update_widget)

        self.setLayout(self._run_layout)
        self.resize(250, 170)

    def exit_procedure(self):
        self.start_time = self.__time_converter(self.time_start.time())
        self.end_time = self.__time_converter(self.time_end.time())
        self.description = self.ln_period_desc.text()
        self.close()

    def __time_converter(self, time):
        seconds = time.hour() * 3_600 + time.minute() * 60 + time.second()
        return seconds

import logging
import os
from os.path import isdir, join

from PyQt5.QtCore import Qt
from aequilibrae.utis.create_example import create_example

from qaequilibrae.modules.common_tools import reporter
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QProgressBar, QLabel, QVBoxLayout, QGroupBox
from qgis.PyQt.QtWidgets import QRadioButton, QGridLayout, QPushButton, QLineEdit
from qgis.PyQt.QtWidgets import QWidget, QFileDialog
from qaequilibrae.modules.common_tools import ReportDialog, standard_path

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class CreateExampleDialog(QtWidgets.QDialog, FROM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)
        self.qgis_project = qgis_project

        self._run_layout = QGridLayout()

        # Area to import network for
        self.select_sfalls = QRadioButton()
        self.select_sfalls.setText("Sioux Falls")
        self.select_sfalls.setChecked(True)

        self.select_nauru = QRadioButton()
        self.select_nauru.setText("Nauru")
        self.select_nauru.setChecked(False)

        self.select_coquimbo = QRadioButton()
        self.select_coquimbo.setText("Coquimbo")
        self.select_coquimbo.setChecked(False)

        self.place = QLineEdit()
        self.place.setVisible(False)

        self.source_type_frame = QVBoxLayout()
        self.source_type_frame.setAlignment(Qt.AlignLeft)
        self.source_type_frame.addWidget(self.select_sfalls)
        self.source_type_frame.addWidget(self.select_nauru)
        self.source_type_frame.addWidget(self.select_coquimbo)

        self.source_type_widget = QGroupBox("Models")
        self.source_type_widget.setLayout(self.source_type_frame)

        # Buttons and output
        self.but_choose_output = QPushButton()
        self.but_choose_output.setText(self.tr("Choose folder output"))
        self.but_choose_output.clicked.connect(self.choose_output)

        self.output_path = QLineEdit()

        self.but_run = QPushButton()
        self.but_run.setText(self.tr("Create"))
        self.but_run.clicked.connect(self.run)

    
    def choose_output(self):
        new_name = QFileDialog.getExistingDirectory(QWidget(), "Parent folder", standard_path())
        if new_name is not None and len(new_name) > 0:
            new_folder = "new_project"
            counter = 1
            while isdir(join(new_name, new_folder)):
                new_folder = f"new_project_{counter}"
                counter += 1
            self.output_path.setText(join(new_name, new_folder))


    def run(self):
        if self.select_sfalls.isChecked():
            place = "sioux_falls"
        elif self.select_nauru.isChecked():
            place = "nauru"
        else:
            place = "coquimbo"

        create_example(self.output_path, place)
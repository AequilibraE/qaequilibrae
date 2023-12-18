import os
from os.path import isdir, join

from PyQt5.QtCore import Qt
from aequilibrae.utils.create_example import create_example

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QVBoxLayout, QGroupBox
from qgis.PyQt.QtWidgets import QRadioButton, QGridLayout, QPushButton, QLineEdit
from qgis.PyQt.QtWidgets import QWidget, QFileDialog
from qaequilibrae.modules.common_tools import standard_path

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class CreateExampleDialog(QtWidgets.QDialog, FORM_CLASS):
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

        self.source_type_frame = QVBoxLayout()
        self.source_type_frame.setAlignment(Qt.AlignLeft)
        self.source_type_frame.addWidget(self.select_sfalls)
        self.source_type_frame.addWidget(self.select_nauru)
        self.source_type_frame.addWidget(self.select_coquimbo)

        self.source_type_widget = QGroupBox("Available models")
        self.source_type_widget.setLayout(self.source_type_frame)

        # Buttons and output
        self.but_choose_output = QPushButton()
        self.but_choose_output.setText(self.tr("Choose folder output"))
        self.but_choose_output.clicked.connect(self.choose_output)

        self.output_path = QLineEdit()

        self.but_run = QPushButton()
        self.but_run.setText(self.tr("Create"))
        self.but_run.clicked.connect(self.run)

        self.buttons_frame = QVBoxLayout()
        self.buttons_frame.addWidget(self.but_choose_output)
        self.buttons_frame.addWidget(self.output_path)
        self.buttons_frame.addWidget(self.but_run)

        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_frame)

        self.update_widget = QWidget()
        self.update_frame = QVBoxLayout()
        self.update_widget.setLayout(self.update_frame)
        self.update_widget.setVisible(False)

        self._run_layout.addWidget(self.source_type_widget)
        self._run_layout.addWidget(self.buttons_widget)
        self._run_layout.addWidget(self.update_widget)

        self.setLayout(self._run_layout)
        self.resize(280, 250)

    
    def choose_output(self):
        if self.select_sfalls.isChecked():
            self.place = "sioux_falls"
        elif self.select_nauru.isChecked():
            self.place = "nauru"
        else:
            self.place = "coquimbo"
    
        new_name = QFileDialog.getExistingDirectory(QWidget(), "Parent folder", standard_path())
        if new_name is not None and len(new_name) > 0:
            new_folder = f"example_{self.place}"
            counter = 1
            while isdir(join(new_name, new_folder)):
                new_folder = f"example_{self.place}_{counter}"
                counter += 1
            self.output_path.setText(join(new_name, new_folder))


    def run(self):

        create_example(self.output_path.text(), self.place)

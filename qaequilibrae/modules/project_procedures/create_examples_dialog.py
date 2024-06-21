import os
from os.path import isdir, join
from pathlib import Path

from aequilibrae.utils.create_example import create_example

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QGridLayout, QPushButton, QLineEdit, QComboBox, QLabel, QVBoxLayout
from qgis.PyQt.QtWidgets import QWidget, QFileDialog
from qaequilibrae.modules.common_tools import standard_path

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class CreateExampleDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        pth = Path(__file__).parent.parent.parent / "packages" / "aequilibrae" / "reference_files"
        models = [str(x.stem) for x in pth.glob("*.zip")]
        print(models)

        self.iface = qgis_project.iface
        self.setupUi(self)
        self.qgis_project = qgis_project

        self._run_layout = QGridLayout()

        lbl = QLabel(self.tr("Available models:"))

        self.cb_models = QComboBox()
        self.cb_models.addItems(models)

        self.but_choose_output = QPushButton()
        self.but_choose_output.setText(self.tr("Choose output folder"))
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

        self._run_layout.addWidget(lbl)
        self._run_layout.addWidget(self.cb_models)
        self._run_layout.addWidget(self.buttons_widget)
        self._run_layout.addWidget(self.update_widget)

        self.setLayout(self._run_layout)
        self.resize(250, 170)

    def choose_output(self):
        self.place = self.cb_models.currentText()

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
        self.close()

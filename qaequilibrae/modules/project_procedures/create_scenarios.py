import sys
from os.path import dirname, join

import qgis
from qgis.PyQt import QtWidgets, uic

sys.modules["qgsmaplayercombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_scenarios.ui"))


class CreateScenariosDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project) -> None:
        QtWidgets.QDialog.__init__(self)
        self.qgis_project = qgis_project
        self.project = qgis_project.project
        self.setupUi(self)

        self.resize(180, 100)

        self.rdo_create.clicked.connect(self.configure_inputs)
        self.rdo_clone.clicked.connect(self.configure_inputs)

        self.but_run.clicked.connect(self.run)

    def configure_inputs(self):
        self.resize(610, 122)

    def run(self):
        name = self.txt_name.text()
        desc = self.txt_desc.text()

        if self.rdo_create.isChecked():
            self.project.create_empty_scenario(name, desc)
        elif self.rdo_clone.isChecked():
            self.project.clone_scenario(name, desc)

        # Update project scenarios
        self.qgis_project.cob_scenarios.clear()
        outdirs = self.project.list_scenarios()["scenario_name"].tolist()
        self.qgis_project.cob_scenarios.addItems(outdirs)

        self.close()

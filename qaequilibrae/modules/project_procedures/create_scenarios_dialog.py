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

        self.rdo_create.toggled.connect(self.configure_inputs)
        self.rdo_clone.toggled.connect(self.configure_inputs)

        self.but_run.clicked.connect(self.run)

        self.populate_scenarios()

    def configure_inputs(self):
        """Update UI elements based on selected mode"""
        if self.rdo_clone.isChecked():
            # Clone mode: show combo box and change label
            self.label_1.setText("Scenario to clone")
            self.txt_name.setVisible(False)
            self.cob_scenarios.setVisible(True)
        else:
            # Create mode: show line edit and change label
            self.label_1.setText("Scenario name")
            self.txt_name.setVisible(True)
            self.cob_scenarios.setVisible(False)

        self.txt_desc.clear()
        self.resize(610, 122)

        # TODO: disable run button if txt_name is empty.

    def populate_scenarios(self):
        """Populate the combo box with available scenarios"""
        scenarios = self.project.list_scenarios()["scenario_name"].tolist()
        
        self.cob_scenarios.clear()
        self.cob_scenarios.addItems(scenarios)

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

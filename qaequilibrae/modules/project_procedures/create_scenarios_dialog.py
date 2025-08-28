from os.path import dirname, join

from qgis.PyQt import QtWidgets, uic

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_scenarios.ui"))


class CreateScenariosDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project) -> None:
        QtWidgets.QDialog.__init__(self)
        self.qgis_project = qgis_project
        self.project = qgis_project.project
        self.setupUi(self)

        self.__init_scenario = self.qgis_project.cob_scenarios.currentText()

        self.rdo_create.clicked.connect(self.configure_inputs)
        self.rdo_clone.clicked.connect(self.configure_inputs)
        self.but_run.clicked.connect(self.run)

        self.populate_scenarios()

    def configure_inputs(self):
        """Update UI elements based on selected mode"""
        if self.rdo_clone.isChecked():
            self.label_1.setVisible(True)
            self.cob_scenarios.setVisible(True)
        if self.rdo_create.isChecked():
            self.label_1.setVisible(False)
            self.cob_scenarios.setVisible(False)

        self.txt_name.clear()
        self.txt_desc.clear()

    def populate_scenarios(self):
        """Populate the combo box with available scenarios. The current text displayed refers to the active scenario."""
        self.cob_scenarios.clear()
        self.cob_scenarios.addItems(self.qgis_project.available_scenarios)
        self.cob_scenarios.setCurrentText(self.__init_scenario)

    def run(self):
        name = self.txt_name.text()
        desc = self.txt_desc.text()

        if self.rdo_clone.isChecked():
            if self.__init_scenario != self.cob_scenarios.currentText():
                self.project.use_scenario(self.cob_scenarios.currentText())
                txt = f"Changing scenario from {self.__init_scenario} to {self.cob_scenarios.currentText()}"
                self.qgis_project.log_message(txt)

            self.project.clone_scenario(name, desc)
            txt = f"Cloned '{self.cob_scenarios.currentText()}'. New scenario '{name}' addeed to the project"
            self.qgis_project.log_message(txt)

            if self.__init_scenario != self.cob_scenarios.currentText():
                self.project.use_scenario(self.__init_scenario)
                txt = f"Changing scenario from {self.cob_scenarios.currentText()} to {self.__init_scenario}"
                self.qgis_project.log_message(txt)
        else:
            self.project.create_empty_scenario(name, desc)
            self.qgis_project.log_message(f"Created empty scenario. New scenario '{name}' addeed to the project")

        # Update project scenarios
        self.qgis_project.cob_scenarios.clear()
        self.qgis_project.available_scenarios.extend([name])
        self.qgis_project.cob_scenarios.addItems(self.qgis_project.available_scenarios)
        self.qgis_project.cob_scenarios.setCurrentText(self.__init_scenario)

        self.close()

from os.path import dirname, join

from qaequilibrae.modules.common_tools import BaseDialog


class CreateScenariosDialog(BaseDialog):
    def __init__(self, qgis_project) -> None:
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_scenarios.ui"), qgis_project=qgis_project)

    def _base_ui_setup(self):
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

            self.project.clone_scenario(name, desc)
            self.qgis_project.message_log(self.tr("Cloned '{}'").format(self.cob_scenarios.currentText()))

            if self.__init_scenario != self.cob_scenarios.currentText():
                self.project.use_scenario(self.__init_scenario)
        else:
            self.project.create_empty_scenario(name, desc)
            self.qgis_project.message_log(self.tr("Created empty scenario"))

        self.qgis_project.message_log(self.tr("New scenario '{}' added to the project").format(name))

        # Update project scenarios
        self.qgis_project.cob_scenarios.clear()
        self.qgis_project.available_scenarios.extend([name])
        self.qgis_project.cob_scenarios.addItems(self.qgis_project.available_scenarios)
        self.qgis_project.cob_scenarios.setCurrentText(self.__init_scenario)

        self.close()

from os.path import dirname, join

from qgis.core import QgsMessageLog, Qgis
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
        self.resize(180, 100)

    def configure_inputs(self):
        """Update UI elements based on selected mode"""
        self.txt_name.clear()
        self.txt_desc.clear()

        # if self.rdo_clone.isChecked():
        #     self.label_1.setVisible(True)
        #     self.cob_scenarios.setVisible(True)
        #     # self.resize(550, 200)
        # else:
        #     self.label_1.setVisible(False)
        #     self.cob_scenarios.setVisible(False)
        #     # self.resize(550, 150)

        self.resize(550, 200)

    def populate_scenarios(self):
        """Populate the combo box with available scenarios"""
        scenarios = self.project.list_scenarios()["scenario_name"].tolist()

        self.cob_scenarios.clear()
        self.cob_scenarios.addItems(scenarios)

        self.cob_scenarios.setCurrentText(self.qgis_project.cob_scenarios.currentText())

    def run(self):
        name = self.txt_name.text()
        desc = self.txt_desc.text()

        if self.rdo_clone.isChecked():
            # Aqui precisamos de uma lógica melhor para que o cenário a ser clonado mude
            # caso não seja o cenário ativo. E esse cenário deve "voltar" ao que era antes
            # ou seja, o valor mostrado em qgis_project.cob_scenarios não pode mudar, mas
            # o novo cenário deve ser clonado a partir do cenário correto.
            if self.__init_scenario != self.cob_scenarios.currentText():
                self.project.use_scenario(self.cob_scenarios.currentText())
                QgsMessageLog.logMessage("Changing scenario for cloning", "Messages", Qgis.Info, False)

            QgsMessageLog.logMessage(
                f"Scenario to be used: {self.cob_scenarios.currentText()}", "Messages", Qgis.Info, False
            )
            self.project.clone_scenario(name, desc)

            self.project.use_scenario(self.__init_scenario)
            QgsMessageLog.logMessage(f"Scenario at menu: {self.__init_scenario}", "Messages", Qgis.Info, False)
        else:
            self.project.create_empty_scenario(name, desc)

        # Update project scenarios
        self.qgis_project.cob_scenarios.clear()
        self.qgis_project.available_scenarios.extend([name])
        self.qgis_project.cob_scenarios.addItems(self.qgis_project.available_scenarios)

        self.close()

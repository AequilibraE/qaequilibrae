import os
from pathlib import Path

from aequilibrae.context import get_logger
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.core import Qgis

from qaequilibrae.message import messages
from qaequilibrae.modules.common_tools import LogDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_run_module.ui"))


class RunModuleDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project, logger=None):
        QDialog.__init__(self)
        self.qgis_project = qgis_project
        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.setupUi(self)

        self.logger = logger or get_logger()

        self.items = list(self.project.run._fields)
        self.cob_function.addItems(self.items)

        self.but_run.clicked.connect(self.run)

    def run(self):
        # Check if selected function is also present at the Parameters file
        func_name = self.items[self.cob_function.currentIndex()]
        parameter_keys = list(self.project.parameters["run"].keys())
        if func_name not in parameter_keys:
            self.iface.messageBar.pushMessage(
                self.tr("Error"), self.tr("Please check the Parameters file"), level=Qgis.Critical, duration=5
            )

        # If the user selects a custom function, check if the run module has a requirements.txt.
        default_funcs = ["example_function_with_kwargs", "graph_summary", "matrix_summary", "results_summary"]
        run_path = Path(self.project.project_base_path / "run" / "requirements.txt")
        if func_name not in default_funcs and os.path.isfile(run_path):
            QMessageBox.question(
                None, "Requirements installation", messages.first_message, QMessageBox.Ok | QMessageBox.Cancel
            )
        else:
            print("no requirements")

        # If so, open a message box asking if one wants to install the missing packages and
        # continue the execution of the `getattr` function. Otherwise, we just exit the procedure.

        func = getattr(self.project.run, func_name)
        result = func()
        self.logger.info(result)

        self.iface.messageBar().pushMessage(self.tr("Run procedures executed"), "", level=Qgis.Info, duration=5)

        self.exit_procedure()

    def exit_procedure(self):
        self.close()

        dlg2 = LogDialog(self.qgis_project, self)
        dlg2.show()
        dlg2.exec_()

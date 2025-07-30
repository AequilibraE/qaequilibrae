import os
import subprocess
from pathlib import Path

from aequilibrae.context import get_logger
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.core import Qgis, QgsMessageLog

from qaequilibrae.download_extra_packages_class import DownloadAll
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

        self.rejected.connect(self.handle_rejection)

        self.check_missing_packages()

        self.but_run.clicked.connect(self.run)

    def handle_rejection(self):
        self.but_run.setVisible(False)
        self.cob_function.setVisible(False)
        self.label.setVisible(False)

    def check_missing_packages(self):
        try:
            self.items = list(self.project.run._fields)
            self.cob_function.addItems(self.items)
            QgsMessageLog.logMessage(
                "All run procedures dependencies are installed.", level=Qgis.MessageLevel.Info, notifyUser=False
            )

        except ModuleNotFoundError:
            run_path = Path(self.project.project_base_path / "run" / "requirements.txt")
            target_dir = Path(__file__).parent.parent.parent / "packages"
            if os.path.isfile(run_path):
                self.question = QMessageBox.question(
                    self, "Missing requirements", self.rp_message, QMessageBox.Ok | QMessageBox.Cancel
                )
                if self.question == QMessageBox.Ok:
                    install_command = f'"{DownloadAll().find_python()}"'
                    install_command += f" -m pip install -r {run_path} --target {target_dir}"
                    QgsMessageLog.logMessage(install_command, level=Qgis.MessageLevel.Info)

                    process = subprocess.Popen(
                        install_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stdin=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                    )
                    for line in process.stdout:
                        QgsMessageLog.logMessage(line.strip(), level=Qgis.MessageLevel.Info)

                    # Check process output
                    exit_code = process.wait()
                    if exit_code != 0:
                        QMessageBox.critical(self, "Error", "Package installation failed. Check messages log.")
                    else:
                        DownloadAll().clean_packages(target_dir)
                        QMessageBox.information(
                            self, "Information", "Restart 'Run Procedures' to validate installation."
                        )
                else:
                    QMessageBox.warning(
                        self, "Warning", "Without the 'requirements.txt' installation, 'Run procedures' cannot be used."
                    )
            else:
                QMessageBox.warning(
                    self, "Warning", "Missing 'requirements.txt' file. Please check the project run folder."
                )
            self.reject()

    def run(self):
        # Check if selected function is also present at the Parameters file
        func_name = self.items[self.cob_function.currentIndex()]
        parameter_keys = list(self.project.parameters["run"].keys())
        if func_name not in parameter_keys:
            self.iface.messageBar.pushMessage(
                self.tr("Error"), self.tr("Please check the Parameters file"), level=Qgis.Critical, duration=5
            )

        func = getattr(self.project.run, func_name)
        result = func()
        if result:
            self.logger.info(result)
        else:
            self.logger.info(f"{func_name} executed. Check for outputs.")

        self.iface.messageBar().pushMessage(self.tr("Run procedures executed"), "", level=Qgis.Info, duration=5)

        self.exit_procedure()

    def exit_procedure(self):
        self.close()

        dlg2 = LogDialog(self.qgis_project, self)
        dlg2.show()
        dlg2.exec_()

    @property
    def rp_message(self):
        """Message for run procedures"""
        a = self.tr("There are missing requirements to run the procedures.")
        b = self.tr("Do you want us to install these missing Python packages?")
        c = self.tr("Without installing the packages, you cannot use 'Run Procedures'.")
        return f"{a}\n{b}\n{c}"

import os
import subprocess
from pathlib import Path

from aequilibrae.context import get_logger
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.core import Qgis

from qaequilibrae.download_extra_packages_class import DownloadAll
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
        self._msg = messages()

        self.rejected.connect(self.handle_rejection)

        self.check_missing_packages()

        self.but_run.clicked.connect(self.run)

    def handle_rejection(self):
        print("FECHA ISSO")
        # self.exit()

    def check_missing_packages(self):
        print("check_missing_packages")
        try:
            self.items = list(self.project.run._fields)
            self.cob_function.addItems(self.items)
        except ModuleNotFoundError:
            run_path = Path(self.project.project_base_path / "run" / "requirements.txt")
            target_dir = Path(__file__).parent.parent.parent / "packages"
            if os.path.isfile(run_path):
                if (
                    QMessageBox.question(
                        self, self._msg.rp_box_name, self._msg.rp_message, QMessageBox.Ok | QMessageBox.Cancel
                    )
                    == QMessageBox.Ok
                ):
                    install_command = f'"{DownloadAll().find_python()}"'
                    install_command += f" -m pip install -r {run_path} --target {target_dir}"
                    print(install_command)
                    process = subprocess.Popen(
                        install_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stdin=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                    )
                    ret = process.stdout.readlines()
                    print(ret)

                    # Verificar código de saída do processo
                    exit_code = process.wait()
                    if exit_code != 0:
                        QMessageBox.information(self, "Information", "Package installation failed.")
                    else:
                        QMessageBox.information(
                            self, "Information", "Restart 'Run Procedures' to validate installation."
                        )
                        self.reject()
                        return
                else:
                    QMessageBox.information(self, "Information", "'Run Procedures' cannot be executed.")
                    self.reject()
                    return
            else:
                QMessageBox.information(self, "Information", self._msg.rp_error)
                self.reject()
                return

    def run(self):
        print("run")
        # Check if selected function is also present at the Parameters file
        func_name = self.items[self.cob_function.currentIndex()]
        parameter_keys = list(self.project.parameters["run"].keys())
        if func_name not in parameter_keys:
            self.iface.messageBar.pushMessage(
                self.tr("Error"), self.tr("Please check the Parameters file"), level=Qgis.Critical, duration=5
            )

        func = getattr(self.project.run, func_name)
        result = func()
        self.logger.info(result)

        self.iface.messageBar().pushMessage(self.tr("Run procedures executed"), "", level=Qgis.Info, duration=5)

        self.exit_procedure()

    def exit_procedure(self):
        print("exit_procedure")
        self.close()

        dlg2 = LogDialog(self.qgis_project, self)
        dlg2.show()
        dlg2.exec_()

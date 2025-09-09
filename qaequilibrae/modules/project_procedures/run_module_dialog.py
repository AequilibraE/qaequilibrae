import subprocess
from os.path import dirname, isfile, join
from pathlib import Path

from aequilibrae.context import get_logger
from qgis.PyQt.QtWidgets import QMessageBox

from qaequilibrae.download_extra_packages_class import DownloadAll
from qaequilibrae.modules.common_tools import LogDialog, BaseDialog


class RunModuleDialog(BaseDialog):
    def __init__(self, qgis_project, logger=None):
        super().__init__(
            ui_file=join(dirname(__file__), "forms/ui_run_module.ui"), qgis_project=qgis_project, logger=logger
        )

    def _base_ui_setup(self, **kwargs):
        self.logger = kwargs.get("logger") or get_logger()

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
            self.qgis_project.message_log("All run procedures dependencies are installed.")

        except ModuleNotFoundError:
            run_path = self.project.project_base_path / "run" / "requirements.txt"
            target_dir = Path(__file__).parent.parent.parent / "packages"
            if isfile(run_path):
                self.question = QMessageBox.question(
                    self, "Missing requirements", self.rp_message, QMessageBox.Ok | QMessageBox.Cancel
                )
                if self.question == QMessageBox.Ok:
                    install_command = f'"{DownloadAll().find_python()}"'
                    install_command += f" -m pip install -r {run_path} --target {target_dir}"
                    self.qgis_project.message_log(install_command)

                    process = subprocess.Popen(
                        install_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stdin=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                    )
                    for line in process.stdout:
                        self.qgis_project.message_log(line.strip())

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
            self.qgis_project.iface_error_message(self.tr("Please check the Parameters file"))

        func = getattr(self.project.run, func_name)
        result = func()
        if result:
            self.logger.info(result)
        else:
            self.logger.info(f"{func_name} executed. Check for outputs.")

        self.qgis_project.iface_info_message("", self.tr("Run procedures executed"))

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

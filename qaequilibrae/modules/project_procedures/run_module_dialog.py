import pprint
import subprocess
import sys
from os.path import dirname, isfile, join
from pathlib import Path

from qgis.PyQt.QtWidgets import QMessageBox

from qaequilibrae.download_extra_packages_class import DownloadAll
from qaequilibrae.modules.common_tools import BaseDialog


class RunModuleDialog(BaseDialog):
    def __init__(self, qgis_project):
        dependencies_dir = qgis_project.project.project_base_path / "run" / "_dependencies"
        if dependencies_dir.exists() and str(dependencies_dir) not in sys.path:
            sys.path.insert(0, str(dependencies_dir))

        super().__init__(ui_file=join(dirname(__file__), "forms/ui_run_module.ui"), qgis_project=qgis_project)

    def _base_ui_setup(self):
        self.do_run = False

        self.rejected.connect(self.handle_rejection)

        self.check_missing_packages()

        if self.do_run:
            self.but_run.clicked.connect(self.run)

    def handle_rejection(self):
        self.but_run.setVisible(False)
        self.cob_function.setVisible(False)
        self.label.setVisible(False)

    def check_missing_packages(self):
        try:
            self.items = list(self.project.run._fields)
            self.cob_function.addItems(self.items)
            self.do_run = True

        except ModuleNotFoundError:
            run_path = self.project.project_base_path / "run" / "requirements.txt"
            target_dir = self.project.project_base_path / "run" / "_dependencies"
            if isfile(run_path):
                self.question = QMessageBox.question(
                    self, "Missing requirements", self.rp_message, QMessageBox.Ok | QMessageBox.Cancel
                )
                if self.question == QMessageBox.Ok:
                    # Create '_dependencies' folder if it does not exist and add a '__init__.py' file
                    Path(target_dir).mkdir(parents=True, exist_ok=True)
                    init_file = target_dir / "__init__.py"
                    if not init_file.exists():
                        init_file.touch()

                    # Prepare installation
                    install_command = f'"{DownloadAll().find_python()}"'
                    install_command += f' -m pip install -r "{run_path}" --target "{target_dir}"'
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

        # Run function and log output
        func = getattr(self.project.run, func_name)
        result = func()

        message = self.tr("Check 'Messages' tab.") if result else ""
        self.qgis_project.iface_success_message(message, self.tr("{} executed").format(func_name))
        if result:
            self.qgis_project.message_log(pprint.pformat(result))

        self.exit_procedure()

    def exit_procedure(self):
        self.close()

    @property
    def rp_message(self):
        """Message for run procedures"""
        a = self.tr("There are missing requirements to run the procedures.")
        b = self.tr("Do you want us to install these missing Python packages?")
        c = self.tr("Without installing the packages, you cannot use 'Run Procedures'.")
        return f"{a}\n{b}\n{c}"

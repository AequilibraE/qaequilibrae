import logging
import pprint
import subprocess
import sys

from os.path import dirname, isfile, join
from pathlib import Path

from qgis.core import QgsTask, QgsApplication, QgsMessageLog, Qgis
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QTextEdit, QCheckBox, QLabel

from qaequilibrae.download_extra_packages_class import DownloadAll
from qaequilibrae.modules.common_tools import BaseDialog


class SafeWrapper:
    # Wrapper class around sys.stdout / sys.stderr to suppress flush() warning in output
    def __init__(self, stream):
        self.stream = stream

    def write(self, msg):
        if self.stream:
            self.stream.write(msg)

    def flush(self):
        if self.stream and hasattr(self.stream, "flush"):
            self.stream.flush()


sys.stdout = SafeWrapper(sys.__stdout__)
sys.stderr = SafeWrapper(sys.__stderr__)


class LogBridge(QObject):
    log_line = pyqtSignal(str)
    stage_line = pyqtSignal(str)
    finished_state = pyqtSignal(bool)  # True = canceled, False = completed


class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Model Run")
        self.resize(700, 450)

        layout = QVBoxLayout()

        self.stage_label = QLabel("")
        layout.addWidget(self.stage_label)

        # Spinner (indeterminate)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        layout.addWidget(self.bar)

        # Log output
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFontFamily("Consolas")
        layout.addWidget(self.text)

        # Auto-scroll toggle
        self.auto_scroll = QCheckBox("Auto scroll")
        self.auto_scroll.setChecked(True)
        layout.addWidget(self.auto_scroll)

        self.setLayout(layout)

    def append(self, msg):
        self.text.append(msg)
        if self.auto_scroll.isChecked():
            self.text.ensureCursorVisible()

    def mark_finished(self):
        # stop spinner
        self.bar.setRange(0, 1)
        self.bar.setValue(1)

    def set_stage(self, msg):
        self.stage_label.setText(msg)


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

    def attach_qgis_logging(self, logger=None, tag="Model Run", task=None):
        logger = logger or logging.getLogger()

        handler = logging.Handler()

        def emit(record):
            try:
                msg = handler.format(record)

                # Map Python logging levels → QGIS levels
                if record.levelno >= logging.ERROR:
                    level = Qgis.Critical
                elif record.levelno >= logging.WARNING:
                    level = Qgis.Warning
                else:
                    level = Qgis.Info

                QgsMessageLog.logMessage(msg, tag, level)

                # thread-safe UI update via signals
                if hasattr(self, "_bridge"):
                    self._bridge.log_line.emit(msg)

                    # Use INFO lines as "current stage" candidates
                    if record.levelno <= logging.INFO:
                        stage = f"{getattr(record, 'indent_str', '')}{record.getMessage()}".strip()
                        self._bridge.stage_line.emit(stage)

                        # Optional: try to update task description if available
                        if task is not None and hasattr(task, "setDescription"):
                            try:
                                task.setDescription(stage[:120])
                            except Exception:
                                pass

            except Exception:
                handler.handleError(record)

        handler.emit = emit

        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)7s - %(indent_str)s%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))

        logger.addHandler(handler)
        return handler

    def run(self):
        func_name = self.items[self.cob_function.currentIndex()]
        parameter_keys = list(self.project.parameters["run"].keys())
        if func_name not in parameter_keys:
            self.qgis_project.iface_error_message(self.tr("Please check the Parameters file"))
            return

        func = getattr(self.project.run, func_name)

        # Open QGIS log panel (dock only; can't force specific tab reliably)
        QgsMessageLog.logMessage("Starting model run ...", "Model Run", Qgis.Info)

        # Signal bridge for thread-safe UI updates
        self._bridge = LogBridge()

        def worker(task, *args, **kwargs):
            import traceback

            # Override dynamic convergence graph update in QGIS (will cause model to freeze)
            from four_step.common.notebooks.dynamic_graph import DynamicGraph
            DynamicGraph.update = lambda self, data: None

            root_logger = logging.getLogger()
            qgis_handler = self.attach_qgis_logging(root_logger, tag="Model Run", task=task)

            try:
                task.setProgress(0)
                QgsMessageLog.logMessage("Model running, please wait ...", "Model Run", Qgis.Info)

                result = func()

                QgsMessageLog.logMessage("Model run finished!", "Model Run", Qgis.Info)
                return result

            except Exception:
                QgsMessageLog.logMessage(traceback.format_exc(), "Model Run", Qgis.Critical)
                raise

            finally:
                root_logger.removeHandler(qgis_handler)

        def finished(exception, result=None):
            canceled = self._task.isCanceled() if hasattr(self, "_task") else False

            if hasattr(self, "log_dialog"):
                self.log_dialog.mark_finished()
                self.log_dialog.append(">>> Model run finished")

            if exception is not None:
                self.qgis_project.iface_error_message(str(exception))
                return

            if canceled:
                self.qgis_project.iface_error_message("Model run canceled")
                return

            message = self.tr("Check 'Messages' tab.") if result else ""
            self.qgis_project.iface_success_message(
                message,
                self.tr("{} executed").format(func_name),
            )

            if result:
                self.qgis_project.message_log(pprint.pformat(result))

            # optional: leave dialog open so user can inspect/save logs
            # self.exit_procedure()

        # Create task FIRST
        self._task = QgsTask.fromFunction(
            f"Running {func_name}",
            worker,
            on_finished=finished,
        )

        # Create dialog with the real task object
        self.log_dialog = LogDialog(self)

        # Connect signals
        self._bridge.log_line.connect(self.log_dialog.append)
        self._bridge.stage_line.connect(self.log_dialog.set_stage)
        self._bridge.finished_state.connect(self.log_dialog.mark_finished)

        self.log_dialog.show()

        # Start task
        QgsApplication.taskManager().addTask(self._task)

    def exit_procedure(self):
        self.close()

    @property
    def rp_message(self):
        """Message for run procedures"""
        a = self.tr("There are missing requirements to run the procedures.")
        b = self.tr("Do you want us to install these missing Python packages?")
        c = self.tr("Without installing the packages, you cannot use 'Run Procedures'.")
        return f"{a}\n{b}\n{c}"

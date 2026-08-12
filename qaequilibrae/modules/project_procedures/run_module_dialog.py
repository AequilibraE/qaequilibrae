import logging
import pprint
import subprocess  # nosec B404
import sys
from os.path import dirname, isfile, join
from pathlib import Path

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsTask
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
)

from qaequilibrae.download_extra_packages_class import DownloadAll
from qaequilibrae.modules.common_tools import BaseDialog

MESSAGE_TAG = "Model Run"


def has_content(result) -> bool:
    """Whether a run procedure returned something worth showing.

    ``bool(result)`` is not enough: procedures may return a DataFrame, and pandas raises
    on the truth value of one.
    """
    if result is None:
        return False
    if hasattr(result, "empty"):  # pandas DataFrame/Series
        return not result.empty
    return bool(result)


def silence_dynamic_convergence_graph() -> None:
    """Stop an ipywidgets convergence chart from freezing the run.

    Models built on top of the notebook helpers draw convergence with an ipywidgets
    ``DynamicGraph``. There is no notebook comm channel inside QGIS, so the redraw blocks
    forever. Models that do not ship the helper are left untouched.
    """
    try:
        from four_step.common.notebooks.dynamic_graph import DynamicGraph
    except ImportError:
        return

    DynamicGraph.update = lambda self, data: None


class StreamRelay:
    """File-like object forwarding whatever a run procedure prints to a callback.

    QGIS runs without a console on Windows, so ``sys.stdout``/``sys.stderr`` can be ``None``
    and a bare ``print()`` inside a procedure raises. Text is buffered until a newline so the
    log shows whole lines, with :meth:`drain` emitting whatever is left at the end of the run.
    """

    def __init__(self, emit, stream=None):
        self._emit = emit
        self._stream = stream
        self._buffer = ""

    def write(self, text):
        if self._stream is not None:
            self._stream.write(text)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line)
        return len(text)

    def flush(self):
        if self._stream is not None:
            self._stream.flush()

    def drain(self):
        if self._buffer:
            self._emit(self._buffer)
            self._buffer = ""

    def isatty(self):
        return False


class OptionalIndentFormatter(logging.Formatter):
    """Formatter that tolerates records without the optional ``indent_str`` attribute.

    Models that nest their logging supply ``indent_str`` through a ``LoggerAdapter``; plain
    AequilibraE records do not, and a missing key would make every line fail to format.
    """

    def format(self, record):
        if not hasattr(record, "indent_str"):
            record.indent_str = ""
        return super().format(record)


class LogBridge(QObject):
    """Carries worker-thread output to the GUI thread through queued signal connections."""

    log_line = pyqtSignal(str)
    stage_line = pyqtSignal(str)


class RunLogDialog(QDialog):
    """Live log and progress indicator for a model run."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Model Run"))
        self.resize(700, 450)

        layout = QVBoxLayout()

        self.stage_label = QLabel("")
        layout.addWidget(self.stage_label)

        # Indeterminate: run procedures report no progress we could scale a bar to
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        layout.addWidget(self.bar)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFontFamily("Consolas")
        layout.addWidget(self.text)

        self.auto_scroll = QCheckBox(self.tr("Auto scroll"))
        self.auto_scroll.setChecked(True)
        layout.addWidget(self.auto_scroll)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def append(self, msg):
        self.text.append(msg)
        if self.auto_scroll.isChecked():
            self.text.ensureCursorVisible()

    def mark_finished(self):
        self.bar.setRange(0, 1)
        self.bar.setValue(1)

    def set_stage(self, msg):
        self.stage_label.setText(msg)


class RunModuleDialog(BaseDialog):
    #: Emitted on the GUI thread once a run has ended, whichever way it ended.
    run_completed = pyqtSignal()

    def __init__(self, qgis_project):
        dependencies_dir = qgis_project.project.project_base_path / "run" / "_dependencies"
        if dependencies_dir.exists() and str(dependencies_dir) not in sys.path:
            sys.path.insert(0, str(dependencies_dir))

        super().__init__(ui_file=join(dirname(__file__), "forms/ui_run_module.ui"), qgis_project=qgis_project)

    def _base_ui_setup(self):
        self.do_run = False
        self.log_dialog = None
        self.task = None
        self.bridge = None

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
                    self,
                    "Missing requirements",
                    self.rp_message,
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                )
                if self.question == QMessageBox.StandardButton.Ok:
                    # Create '_dependencies' folder if it does not exist and add a '__init__.py' file
                    Path(target_dir).mkdir(parents=True, exist_ok=True)
                    init_file = target_dir / "__init__.py"
                    if not init_file.exists():
                        init_file.touch()

                    # Prepare installation
                    install_command = [str(DownloadAll().find_python())]
                    install_command += ["-m", "pip", "install", "-r", str(run_path), "--target", str(target_dir)]
                    self.qgis_project.message_log(" ".join(install_command))

                    # Argument list, no shell: every element is either a literal or a path we resolved ourselves
                    process = subprocess.Popen(  # nosec B603
                        install_command,
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

    def attach_qgis_logging(self, logger=None, tag=MESSAGE_TAG, bridge=None):
        """Mirror every record on ``logger`` into the QGIS message log and the run dialog.

        Attached to the root logger, so AequilibraE's own logger and anything the model logs
        are both picked up. The caller owns the returned handler and must remove it.
        """
        logger = logger or logging.getLogger()
        bridge = bridge or self.bridge

        handler = logging.Handler()

        def emit(record):
            try:
                msg = handler.format(record)

                if record.levelno >= logging.ERROR:
                    level = Qgis.MessageLevel.Critical
                elif record.levelno >= logging.WARNING:
                    level = Qgis.MessageLevel.Warning
                else:
                    level = Qgis.MessageLevel.Info

                QgsMessageLog.logMessage(msg, tag, level)

                if bridge is not None:
                    bridge.log_line.emit(msg)

                    # Info lines double as the "what is happening now" caption
                    if record.levelno <= logging.INFO:
                        stage = f"{getattr(record, 'indent_str', '')}{record.getMessage()}".strip()
                        bridge.stage_line.emit(stage)

            except Exception:
                # A logging handler must never raise back into whatever was being logged
                handler.handleError(record)

        handler.emit = emit
        handler.setFormatter(
            OptionalIndentFormatter(
                "%(asctime)s - %(levelname)7s - %(indent_str)s%(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

        logger.addHandler(handler)
        return handler

    def run(self):
        # Check if selected function is also present at the Parameters file
        func_name = self.items[self.cob_function.currentIndex()]
        parameter_keys = list(self.project.parameters["run"].keys())
        if func_name not in parameter_keys:
            self.qgis_project.iface_error_message(self.tr("Please check the Parameters file"))
            return

        func = getattr(self.project.run, func_name)

        self.but_run.setEnabled(False)

        # The run outlives this dialog if the user closes it, so hold the scenario lock for the
        # duration of the task rather than only until 'finished' fires on the dialog
        self.qgis_project.block_change_scenario()

        self.bridge = LogBridge()
        if self.log_dialog is not None and not sip.isdeleted(self.log_dialog):
            # Log windows from earlier runs stay parented to this dialog otherwise
            self.log_dialog.deleteLater()
        self.log_dialog = RunLogDialog(self)
        self.bridge.log_line.connect(self.log_dialog.append)
        self.bridge.stage_line.connect(self.log_dialog.set_stage)
        self.log_dialog.show()

        QgsMessageLog.logMessage(self.tr("Starting model run..."), MESSAGE_TAG, Qgis.MessageLevel.Info)

        # QgsTaskWrapper.finished() does 'if self.returned_values:' on whatever the worker
        # returns, which raises for a DataFrame or an array and swallows the completion
        # callback with it. Hand the result over on the side and return nothing.
        outcome = {}
        self.task = QgsTask.fromFunction(
            self.tr("Running {}").format(func_name),
            self._worker(func, outcome),
            on_finished=self._on_finished(func_name, outcome),
        )
        QgsApplication.taskManager().addTask(self.task)

    def _worker(self, func, outcome):
        """Build the callable the task manager runs on a background thread.

        Everything the worker needs is bound here, on the GUI thread, so the background thread
        never touches the dialog.
        """
        bridge = self.bridge
        running_msg = self.tr("Model running, please wait...")
        done_msg = self.tr("Model run finished!")

        # The task manager always passes the task in, even though nothing here needs it
        def worker(task):
            import traceback

            silence_dynamic_convergence_graph()

            root_logger = logging.getLogger()
            handler = self.attach_qgis_logging(root_logger, bridge=bridge)

            # Procedures print as much as they log, and QGIS may leave us without a console
            relay = StreamRelay(bridge.log_line.emit, sys.__stdout__)
            stdout, stderr = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = relay

            try:
                QgsMessageLog.logMessage(running_msg, MESSAGE_TAG, Qgis.MessageLevel.Info)
                outcome["result"] = func()
                QgsMessageLog.logMessage(done_msg, MESSAGE_TAG, Qgis.MessageLevel.Info)

            except Exception:
                QgsMessageLog.logMessage(traceback.format_exc(), MESSAGE_TAG, Qgis.MessageLevel.Critical)
                raise

            finally:
                sys.stdout, sys.stderr = stdout, stderr
                relay.drain()
                root_logger.removeHandler(handler)

        return worker

    def _on_finished(self, func_name, outcome):
        """Build the completion callback, which the task manager calls on the GUI thread.

        Messages are translated up front so the callback never calls into the dialog's C++ side,
        which the user may have closed by the time the run ends.
        """
        finished_msg = self.tr(">>> Model run finished")
        canceled_msg = self.tr("Model run canceled")
        check_msg = self.tr("Check 'Messages' tab.")
        executed_msg = self.tr("{} executed").format(func_name)

        def finished(exception, _result=None):
            canceled = self.task is not None and self.task.isCanceled()
            result = outcome.get("result")
            self.task = None
            self.bridge = None
            self.qgis_project.allow_change_scenario()

            alive = not sip.isdeleted(self)

            if alive:
                self.but_run.setEnabled(True)
                if self.log_dialog is not None and not sip.isdeleted(self.log_dialog):
                    self.log_dialog.mark_finished()
                    self.log_dialog.append(finished_msg)

            try:
                # A canceled task also arrives with a generic exception, so check it first
                if canceled:
                    self.qgis_project.iface_error_message(canceled_msg)
                    return

                if exception is not None:
                    self.qgis_project.iface_error_message(str(exception))
                    return

                message = check_msg if has_content(result) else ""
                self.qgis_project.iface_success_message(message, executed_msg)

                if has_content(result):
                    self.qgis_project.message_log(pprint.pformat(result))
            finally:
                if alive:
                    self.run_completed.emit()

        return finished

    def exit_procedure(self):
        self.close()

    @property
    def rp_message(self):
        """Message for run procedures"""
        a = self.tr("There are missing requirements to run the procedures.")
        b = self.tr("Do you want us to install these missing Python packages?")
        c = self.tr("Without installing the packages, you cannot use 'Run Procedures'.")
        return f"{a}\n{b}\n{c}"

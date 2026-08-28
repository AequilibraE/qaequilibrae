import logging
import pprint
import re
import subprocess  # nosec B404
import sys
from os.path import dirname, isfile, join
from pathlib import Path

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsTask
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QTimer, pyqtSignal
from qgis.PyQt.QtWidgets import QMessageBox

from qaequilibrae.download_extra_packages_class import DownloadAll
from qaequilibrae.modules.common_tools import BaseDialog, LiveLogBridge, LiveLogDialog

MESSAGE_TAG = "Model Run"


def has_content(result) -> bool:
    """Return whether a run result is worth reporting."""
    if result is None:
        return False
    if hasattr(result, "empty"):  # pandas DataFrame/Series
        return not result.empty
    return bool(result)


def silence_dynamic_convergence_graph() -> None:
    """Disable notebook-only convergence redraws inside QGIS."""
    try:
        from four_step.common.notebooks.dynamic_graph import DynamicGraph
    except ImportError:
        return

    DynamicGraph.update = lambda self, data: None


class StreamRelay:
    """Line-buffered stdout/stderr relay."""

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
    def format(self, record):
        if not hasattr(record, "indent_str"):
            record.indent_str = ""
        return super().format(record)


LogBridge = LiveLogBridge


class RunLogDialog(LiveLogDialog):
    def __init__(self, parent=None):
        super().__init__("", parent=parent, initial_indeterminate=True)
        self.setWindowTitle(self.tr("Model Run"))


class LogTailer:
    """Follow a scenario's ``aequilibrae.log`` and relay whatever gets appended"""

    line_pattern = re.compile(r"^\d{4}-\d{2}-\d{2} [\d:,]+;(\w+)\s*;\s?(.*)$")

    def __init__(self, path, emit_line, emit_stage=None, tag=MESSAGE_TAG):
        self.path = Path(path)
        self.tag = tag
        self._emit_line = emit_line
        self._emit_stage = emit_stage
        # Start at the end. The log accumulates across runs, and only what this run
        # appends belongs in its dialog.
        self.position = self.path.stat().st_size if self.path.is_file() else 0
        self._carry = b""

    def poll(self):
        """Relay every complete line written since the last call."""
        if not self.path.is_file():
            return

        size = self.path.stat().st_size
        if size < self.position:
            # Truncated or replaced underneath us -- reopening a project rewrites it.
            self.position = 0
            self._carry = b""
        if size == self.position and not self._carry:
            return

        # Byte offsets throughout: a text-mode tell() returns an opaque cookie that
        # cannot be compared against st_size.
        with open(self.path, "rb") as handle:
            handle.seek(self.position)
            chunk = handle.read()
            self.position = handle.tell()

        head, separator, self._carry = (self._carry + chunk).rpartition(b"\n")
        if not separator:
            return
        for raw in head.split(b"\n"):
            line = raw.decode("utf-8", errors="replace").rstrip("\r")
            if line:
                self._relay(line)

    def _relay(self, line):
        match = self.line_pattern.match(line)
        level = logging.getLevelName(match.group(1)) if match else logging.INFO
        if not isinstance(level, int):
            level = logging.INFO

        if level >= logging.ERROR:
            qgis_level = Qgis.MessageLevel.Critical
        elif level >= logging.WARNING:
            qgis_level = Qgis.MessageLevel.Warning
        else:
            qgis_level = Qgis.MessageLevel.Info

        QgsMessageLog.logMessage(line, self.tag, qgis_level)
        self._emit_line(line)

        # Info lines double as the "what is happening now" caption
        if self._emit_stage is not None and level <= logging.INFO:
            stage = (match.group(2) if match else line).strip()
            if stage:
                self._emit_stage(stage)


class RunModuleDialog(BaseDialog):
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
        self.tailer = None
        self.log_timer = None

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

    def _start_tailing(self):
        """Begin following the active scenario's log file on the GUI thread."""
        self.tailer = LogTailer(
            self.project.project_base_path / "aequilibrae.log",
            self.bridge.log_line.emit,
            self.bridge.stage_line.emit,
        )
        self.log_timer = QTimer(self)
        self.log_timer.setInterval(300)
        self.log_timer.timeout.connect(self.tailer.poll)
        self.log_timer.start()

    def _stop_tailing(self):
        """Stop following the log, relaying whatever arrived since the last tick."""
        if self.log_timer is not None:
            self.log_timer.stop()
            self.log_timer.deleteLater()
            self.log_timer = None
        if self.tailer is not None:
            self.tailer.poll()
            self.tailer = None

    def run(self):
        # Check if selected function is also present at the Parameters file
        func_name = self.items[self.cob_function.currentIndex()]
        parameter_keys = list(self.project.parameters["run"].keys())
        if func_name not in parameter_keys:
            self.qgis_project.iface_error_message(self.tr("Please check the Parameters file"))
            return

        func = getattr(self.project.run, func_name)

        self.but_run.setEnabled(False)

        self.qgis_project.block_change_scenario()

        self.bridge = LogBridge()
        if self.log_dialog is not None and not sip.isdeleted(self.log_dialog):
            # Log windows from earlier runs stay parented to this dialog otherwise
            self.log_dialog.deleteLater()
        self.log_dialog = RunLogDialog(self)
        self.log_dialog.connect_bridge(self.bridge)
        self.log_dialog.show()

        # Follow the active scenario's log rather than attaching a handler to the
        # root logger, which AequilibraE's per-project logger never reaches. The
        # scenario cannot change while a run is blocked, so the path is stable.
        self._start_tailing()

        QgsMessageLog.logMessage(self.tr("Starting model run..."), MESSAGE_TAG, Qgis.MessageLevel.Info)

        # Avoid QgsTaskWrapper truth-testing DataFrames/arrays on completion.
        outcome = {}
        self.task = QgsTask.fromFunction(
            self.tr("Running {}").format(func_name),
            self._worker(func, outcome),
            on_finished=self._on_finished(func_name, outcome),
        )
        QgsApplication.taskManager().addTask(self.task)

    def _worker(self, func, outcome):
        """Build the background callable without touching dialog state there."""
        bridge = self.bridge
        running_msg = self.tr("Model running, please wait...")
        done_msg = self.tr("Model run finished!")

        # The task manager always passes the task in, even though nothing here needs it
        def worker(task):
            import traceback

            silence_dynamic_convergence_graph()

            # Log records reach the dialog by way of the scenario's log file; only
            # stdout/stderr (progress bars, prints) still need relaying from here.
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

        return worker

    def _on_finished(self, func_name, outcome):
        """Build the GUI-thread completion callback."""
        finished_msg = self.tr(">>> Model run finished")
        canceled_msg = self.tr("Model run canceled")
        check_msg = self.tr("Check 'Messages' tab.")
        executed_msg = self.tr("{} executed").format(func_name)

        def finished(exception, _result=None):
            canceled = self.task is not None and self.task.isCanceled()
            result = outcome.get("result")
            self.task = None
            self._stop_tailing()
            self.bridge = None
            self.qgis_project.allow_change_scenario()

            alive = not sip.isdeleted(self)

            if alive:
                self.but_run.setEnabled(True)
                if self.log_dialog is not None and not sip.isdeleted(self.log_dialog):
                    self.log_dialog.mark_finished()
                    self.log_dialog.append(finished_msg)

            try:
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

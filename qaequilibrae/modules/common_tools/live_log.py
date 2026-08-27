from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class LiveLogBridge(QObject):
    log_line = pyqtSignal(str)
    stage_line = pyqtSignal(str)
    progress_started = pyqtSignal(int, str)
    progress_updated = pyqtSignal(int)
    progress_reset = pyqtSignal()
    finished = pyqtSignal()


class LiveLogWidget(QWidget):
    def __init__(self, parent=None, *, initial_indeterminate=False, line_wrap=False):
        super().__init__(parent)

        layout = QVBoxLayout()

        self.stage_label = QLabel("")
        layout.addWidget(self.stage_label)

        self.bar = QProgressBar()
        layout.addWidget(self.bar)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        if not line_wrap:
            self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text.setMaximumBlockCount(5000)

        log_font = QFont()
        log_font.setFamily("Consolas")
        log_font.setFixedPitch(True)
        log_font.setPointSize(9)
        self.text.setFont(log_font)
        layout.addWidget(self.text)

        self.auto_scroll = QCheckBox(self.tr("Auto scroll"))
        self.auto_scroll.setChecked(True)
        layout.addWidget(self.auto_scroll)

        self.setLayout(layout)

        if initial_indeterminate:
            self.set_indeterminate()
        else:
            self.reset_progress()

    def append(self, msg):
        if not msg:
            return
        self.text.appendPlainText(msg)
        if self.auto_scroll.isChecked():
            # Drive the scrollbar rather than the cursor. appendPlainText leaves the
            # text cursor where it was -- usually the very start -- so asking to make
            # the cursor visible scrolls back to the top instead of following the tail.
            scrollbar = self.text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def connect_bridge(self, bridge):
        bridge.log_line.connect(self.append)
        bridge.stage_line.connect(self.set_stage)
        bridge.progress_started.connect(self.start_progress)
        bridge.progress_updated.connect(self.set_progress)
        bridge.progress_reset.connect(self.reset_progress)
        bridge.finished.connect(self.mark_finished)

    def clear(self):
        self.text.clear()
        self.stage_label.clear()
        self.reset_progress()

    def mark_finished(self):
        self.bar.setRange(0, 1)
        self.bar.setValue(1)

    def reset_progress(self):
        self.bar.setRange(0, 1)
        self.bar.reset()

    def set_indeterminate(self):
        self.bar.setRange(0, 0)

    def set_stage(self, msg):
        self.stage_label.setText(msg)

    def start_progress(self, maximum, msg):
        self.stage_label.setText(msg)
        self.bar.setRange(0, maximum)
        self.bar.setValue(0)

    def set_progress(self, value):
        self.bar.setValue(value)


def connect_progress_widgets(bridge, progressbar, progress_label, *, clear_on_finished=True):
    def start_progress(maximum, msg):
        progress_label.setText(msg)
        progressbar.setValue(0)
        progressbar.setMaximum(maximum)

    def reset_progress():
        progressbar.reset()

    def finish_progress():
        progressbar.reset()
        if clear_on_finished:
            progress_label.clear()

    bridge.progress_started.connect(start_progress)
    bridge.progress_updated.connect(progressbar.setValue)
    bridge.progress_reset.connect(reset_progress)
    bridge.stage_line.connect(progress_label.setText)
    bridge.finished.connect(finish_progress)


class LiveLogDialog(QDialog):
    def __init__(self, title, parent=None, *, initial_indeterminate=False):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(700, 450)

        layout = QVBoxLayout()

        self.log = LiveLogWidget(self, initial_indeterminate=initial_indeterminate)
        layout.addWidget(self.log)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)
        self.auto_scroll = self.log.auto_scroll
        self.bar = self.log.bar
        self.stage_label = self.log.stage_label
        self.text = self.log.text

    def append(self, msg):
        self.log.append(msg)

    def connect_bridge(self, bridge):
        self.log.connect_bridge(bridge)

    def mark_finished(self):
        self.log.mark_finished()

    def set_stage(self, msg):
        self.log.set_stage(msg)

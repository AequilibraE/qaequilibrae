from os.path import isdir, isfile, join, dirname

import qgis
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QProgressBar, QLabel, QVBoxLayout, QGroupBox, QPlainTextEdit
from qgis.PyQt.QtWidgets import QRadioButton, QGridLayout, QPushButton, QLineEdit
from qgis.PyQt.QtWidgets import QWidget, QFileDialog, QDialog
from qgis.core import QgsProject, QgsCoordinateReferenceSystem

from qaequilibrae.modules.common_tools import ReportDialog, standard_path
from qaequilibrae.modules.project_procedures.project_from_osm_procedure import ProjectFromOSMProcedure

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "../common_tools/forms/ui_empty.ui"))

log_refresh_interval = 250  # milliseconds


class ProjectFromOSMDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)
        self.qgis_project = qgis_project

        self.path = standard_path()
        self.error = None
        self.report = []
        self.worker_thread = None
        self.running = False
        self.logfile = None
        self.__log_position = 0
        self._run_layout = QGridLayout()

        # Area to import network for
        self.choose_place = QRadioButton()
        self.choose_place.setText(self.tr("Place name"))
        self.choose_place.toggled.connect(self.change_place_type)
        self.choose_place.setChecked(False)

        self.choose_canvas = QRadioButton()
        self.choose_canvas.setText(self.tr("Current map canvas area"))
        self.choose_canvas.setChecked(True)

        self.place = QLineEdit()
        self.place.setVisible(False)

        self.source_type_frame = QVBoxLayout()
        self.source_type_frame.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.source_type_frame.addWidget(self.choose_place)
        self.source_type_frame.addWidget(self.choose_canvas)
        self.source_type_frame.addWidget(self.place)

        self.source_type_widget = QGroupBox(self.tr("Target"))
        self.source_type_widget.setLayout(self.source_type_frame)

        # Buttons and output
        self.but_choose_output = QPushButton()
        self.but_choose_output.setText(self.tr("Choose folder output"))
        self.but_choose_output.clicked.connect(self.choose_output)

        self.output_path = QLineEdit()

        self.but_run = QPushButton()
        self.but_run.setText(self.tr("Import network and create project"))
        self.but_run.clicked.connect(self.run)

        self.buttons_frame = QVBoxLayout()
        self.buttons_frame.addWidget(self.but_choose_output)
        self.buttons_frame.addWidget(self.output_path)
        self.buttons_frame.addWidget(self.but_run)

        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_frame)

        self.progressbar = QProgressBar()
        self.progress_label = QLabel()

        # The network import is long enough that the log is the only way of telling what it is doing
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setMaximumBlockCount(5000)
        log_font = QFont()
        log_font.setFamily("Courier")
        log_font.setFixedPitch(True)
        log_font.setPointSize(9)
        self.log_view.setFont(log_font)

        self.log_timer = QTimer(self)
        self.log_timer.setInterval(log_refresh_interval)
        self.log_timer.timeout.connect(self.refresh_log)

        self.update_widget = QWidget()
        self.update_frame = QVBoxLayout()
        self.update_frame.addWidget(self.progressbar)
        self.update_frame.addWidget(self.progress_label)
        self.update_frame.addWidget(self.log_view)
        self.update_widget.setLayout(self.update_frame)
        self.update_widget.setVisible(False)

        self._run_layout.addWidget(self.source_type_widget)
        self._run_layout.addWidget(self.buttons_widget)
        self._run_layout.addWidget(self.update_widget)
        self._run_layout.setRowStretch(2, 1)

        self.setLayout(self._run_layout)
        self.resize(280, 250)

    def choose_output(self):
        new_name = QFileDialog.getExistingDirectory(QWidget(), "Parent folder", standard_path())
        if new_name is not None and len(new_name) > 0:
            new_folder = "new_project"
            counter = 1
            while isdir(join(new_name, new_folder)):
                new_folder = f"new_project_{counter}"
                counter += 1
            self.output_path.setText(join(new_name, new_folder))

    def run(self):
        if self.running:
            return

        if self.choose_canvas.isChecked():
            QgsProject.instance().setCrs(QgsCoordinateReferenceSystem.fromEpsgId(4326))
            e = self.iface.mapCanvas().extent()
            bbox = [e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum()]
            place_name = None
        else:
            bbox = None
            place_name = self.place.text()

        self.error = None
        self.report = []
        self.update_widget.setVisible(True)
        self.source_type_widget.setEnabled(False)
        self.but_choose_output.setEnabled(False)
        self.output_path.setEnabled(False)
        self.but_run.setEnabled(False)
        self.resize(700, 500)

        self.running = True
        self.start_tailing_log()

        self.worker_thread = ProjectFromOSMProcedure(
            qgis.utils.iface.mainWindow(), self.output_path.text(), bbox=bbox, place_name=place_name
        )
        self.worker_thread.signal.connect(self.signal_handler)
        self.worker_thread.start()

    def change_place_type(self):
        if self.choose_place.isChecked():
            self.place.setVisible(True)
        else:
            self.place.setVisible(False)

    def start_tailing_log(self):
        """AequilibraE only opens the log file when it creates the project, so we tail it as it appears"""
        self.logfile = join(self.output_path.text(), "aequilibrae.log")
        self.__log_position = 0
        self.log_view.clear()
        self.log_timer.start()

    def refresh_log(self):
        if self.logfile is None or not isfile(self.logfile):
            return

        # This runs on a timer, and PyQt turns an exception crossing a slot boundary into a
        # qFatal() - so a log we cannot read has to cost us the tick, not the QGIS session.
        # No encoding is given on purpose, to match the one AequilibraE writes the file with
        try:
            with open(self.logfile, "r", errors="replace") as log:
                log.seek(self.__log_position)
                new_entries = log.read()
                self.__log_position = log.tell()
        except OSError:
            return

        if not new_entries.strip():
            return

        self.log_view.appendPlainText(new_entries.strip("\n"))
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def leave(self):
        self.close()
        dlg2 = ReportDialog(self.iface, self.report)
        dlg2.show()
        dlg2.exec()

    def signal_handler(self, val):
        if val[0] == "start":
            self.progress_label.setText(val[2])
            self.progressbar.setValue(0)
            self.progressbar.setMaximum(val[1])
        elif val[0] == "update":
            self.progressbar.setValue(val[1])
        elif val[0] == "set_text":
            self.progress_label.setText(val[1])
            self.progressbar.reset()
        elif val[0] == "finished":
            self.job_finished()

    def job_finished(self):
        self.log_timer.stop()
        self.refresh_log()
        self.running = False

        self.report.extend(self.worker_thread.report)
        self.error = self.worker_thread.error

        if self.error is not None:
            self.failed_to_import()
            return

        self.qgis_project.project = self.worker_thread.project
        self.leave()

    def failed_to_import(self):
        """Lets the user fix whatever went wrong and try again, rather than losing the log they can see"""
        try:
            if self.worker_thread.project is not None:
                self.worker_thread.project.close()
        except Exception:
            # A project that failed halfway through is not worth a second error message
            pass

        self.progress_label.setText(self.error)
        self.progressbar.reset()
        self.qgis_project.iface_error_message(self.error, self.tr("Could not import network from OSM"))

        self.source_type_widget.setEnabled(True)
        self.but_choose_output.setEnabled(True)
        self.output_path.setEnabled(True)
        self.but_run.setEnabled(True)

    # The import cannot be interrupted, and letting the dialog go while the thread still
    # reports back to it would take QGIS down with it
    def closeEvent(self, event):
        if self.running:
            event.ignore()
        else:
            super().closeEvent(event)

    def reject(self):
        if not self.running:
            super().reject()

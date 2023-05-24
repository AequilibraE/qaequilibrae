import logging
import os

# from aequilibrae.transit.gtfs import create_gtfsdb

import qgis
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QRadioButton, QGridLayout, QPushButton, QHBoxLayout, QWidget, QLineEdit
from qgis.PyQt.QtWidgets import QSpacerItem, QProgressBar, QLabel, QVBoxLayout, QSizePolicy, QCheckBox
from ..common_tools import ReportDialog, GetOutputFileName, GetOutputFolderName
from ..common_tools import standard_path

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class GtfsImportDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.path = standard_path()
        self.output_path = None
        self.temp_path = None
        self.error = None
        self.report = None
        self.worker_thread = None
        self.running = False
        self.logger = logging.getLogger("aequilibrae")

        self._run_layout = QGridLayout()

        # Source type for the GTFS
        self.choose_zip = QRadioButton()
        self.choose_zip.setText("Source is zip file")
        self.choose_zip.setChecked(True)

        self.choose_folder = QRadioButton()
        self.choose_folder.setText("Source is folder")
        self.choose_folder.setChecked(False)

        self.source_type_frame = QHBoxLayout()
        self.source_type_frame.addWidget(self.choose_zip)
        self.source_type_frame.addWidget(self.choose_folder)
        self.source_type_widget = QWidget()
        self.source_type_widget.setLayout(self.source_type_frame)

        # Source GTFS
        self.but_choose_gtfs = QPushButton()
        self.but_choose_gtfs.clicked.connect(self.find_input)
        self.but_choose_gtfs.setFixedSize(100, 30)
        self.but_choose_gtfs.setText("GTFS Source")
        self.gtfs_source = QLineEdit()
        self.source_frame = QHBoxLayout()
        self.source_frame.addWidget(self.but_choose_gtfs, 1)
        self.source_frame.addWidget(self.gtfs_source, 0)
        self.source_widget = QWidget()
        self.source_widget.setLayout(self.source_frame)

        # Output sqlite
        self.but_choose_dest = QPushButton()
        self.but_choose_dest.clicked.connect(self.set_output_db)
        self.but_choose_dest.setFixedSize(100, 30)
        self.but_choose_dest.setText("Output")
        self.gtfs_output = QLineEdit()
        output_frame = QHBoxLayout()
        output_frame.addWidget(self.but_choose_dest, 1)
        output_frame.addWidget(self.gtfs_output, 0)
        self.output_widget = QWidget()
        self.output_widget.setLayout(output_frame)

        # Spatialite or not
        self.spatial = QCheckBox()
        self.spatial.setChecked(True)
        self.spatial.setText("Create spatial components")
        options_frame = QHBoxLayout()
        options_frame.addWidget(self.spatial, 1)
        self.options_widget = QWidget()
        self.options_widget.setLayout(options_frame)

        # action buttons
        self.but_process = QPushButton()
        self.but_process.setText("Run")
        self.but_process.clicked.connect(self.run)

        self.but_cancel = QPushButton()
        self.but_cancel.setText("Cancel")
        self.but_cancel.clicked.connect(self.exit_procedure)

        spacer = QSpacerItem(5, 5, QSizePolicy.Expanding, QSizePolicy.Minimum)
        but_frame = QHBoxLayout()
        but_frame.addWidget(self.but_cancel, 1)
        but_frame.addItem(spacer)
        but_frame.addWidget(self.but_process, 1)
        self.but_widget = QWidget()
        self.but_widget.setLayout(but_frame)

        # Progress bars and messagers
        self.progress_frame = QVBoxLayout()
        self.status_bar_files = QProgressBar()
        self.progress_frame.addWidget(self.status_bar_files)

        self.status_label_file = QLabel()
        self.status_label_file.setText("Extracting: ")
        self.progress_frame.addWidget(self.status_label_file)

        self.status_bar_chunks = QProgressBar()
        self.progress_frame.addWidget(self.status_bar_chunks)

        self.progress_widget = QWidget()
        self.progress_widget.setLayout(self.progress_frame)
        self.progress_widget.setVisible(False)

        self._run_layout.addWidget(self.progress_widget)
        self._run_layout.addWidget(self.source_widget)
        self._run_layout.addWidget(self.source_type_widget)
        self._run_layout.addWidget(self.output_widget)
        self._run_layout.addWidget(self.options_widget)
        self._run_layout.addWidget(self.but_widget)

        self.setLayout(self._run_layout)
        self.resize(600, 135)

    def run_thread(self):

        self.worker_thread.converting_gtfs.connect(self.signal_handler)

        self.worker_thread.import_gtfs()
        self.exec_()

    def find_input(self):
        if self.choose_zip.isChecked():
            new_name, type = GetOutputFileName(self, "GTFS Feed", ["Zip containers(*.zip)"], ".zip", self.path)
        else:
            new_name = GetOutputFolderName(self.path, "GTFS Feed")

        if new_name is not None:
            self.gtfs_source.setText(new_name)

    def set_output_db(self):
        new_name, type = GetOutputFileName(
            self, "SQLite Database", ["SQLite(*.sqlite)", "SQLite(*.db)"], ".sqlite", self.path
        )
        if new_name is not None:
            self.gtfs_output.setText(new_name)

    def job_finished_from_thread(self):
        self.report = self.worker_thread.report

        self.exit_procedure()

    def run(self):
        data_source = self.gtfs_source.text()
        output_file = self.gtfs_output.text()
        if not os.path.isfile(data_source):
            if not os.path.isdir(data_source):
                qgis.utils.iface.messageBar().pushMessage("Data source does not exist", "", level=3)
                return

        self.running = True
        self.source_widget.setVisible(False)
        self.output_widget.setVisible(False)
        self.but_process.setEnabled(False)
        self.options_widget.setVisible(False)
        self.source_type_widget.setVisible(False)
        self.progress_widget.setVisible(True)

        self.logger.info(data_source)
        self.worker_thread = create_gtfsdb(
            data_source, save_db=output_file, overwrite=True, spatialite_enabled=self.spatial.isChecked()
        )
        self.run_thread()

    def signal_handler(self, val):
        if val[0] == "text":
            self.status_label_file.setText(val[1])

        elif val[0] == "files counter":
            self.status_bar_files.setValue(val[1])

        elif val[0] == "total files":
            self.status_bar_files.setMaximum(val[1])

        elif val[0] == "chunk counter":
            self.status_bar_chunks.setValue(val[1])

        elif val[0] == "max chunk counter":
            self.status_bar_chunks.setMaximum(val[1])

        elif val[0] == "finished_threaded_procedure":
            self.job_finished_from_thread()

    def exit_procedure(self):
        self.close()
        if self.running:
            self.worker_thread.stop()
        if self.report:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()

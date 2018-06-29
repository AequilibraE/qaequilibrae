"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       GTFS import
 Purpose:    Loads interface for converting GTFS to SQLite with Spatialite database

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:   Pedro Camargo
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2018-02-02
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, uic
from qgis.gui import QgsMapLayerProxyModel
import sys
from functools import partial
import numpy as np
from collections import OrderedDict

from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import *
from ..common_tools import ReportDialog
from ..common_tools import GetOutputFileName
from PyQt4.QtGui import QHBoxLayout, QVBoxLayout, QGridLayout
from PyQt4.QtGui import QProgressBar, QLabel, QWidget, QPushButton, QSpacerItem

from ..aequilibrae.aequilibrae.transit.gtfs import gtfs_sqlite_db

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '../common_tools/forms/ui_empty.ui'))


class GtfsImportDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.path = standard_path()
        self.output_path = None
        self.temp_path = None
        self.error = None
        self.report = None
        self.worker_thread = None
        self.running = False
        self.data_path, self.data_type = GetOutputFileName(self, 'GTFS Feeds in ZIP format',
                                                           ["GTFS Feed(*.zip)"], '.zip', standard_path())

        if self.data_path is None:
            self.exit_procedure()

        self.output_path, data_type = GetOutputFileName(self, 'SpatiaLite table',
                                                        ["Sqlite(*.sqlite)"], '.sqlite', standard_path())

        if self.data_path is None:
            self.exit_procedure()


        self._run_layout = QGridLayout()

        # We know how many files we will have, so we can do some of the setup now
        self.status_bar_files = QProgressBar()
        self.status_label_file = QLabel()
        self.status_label_file.setText('Extracting: ' + self.data_path)
        self._run_layout.addWidget(self.status_bar_files)
        self._run_layout.addWidget(self.status_label_file)

        self.status_bar_chunks = QProgressBar()
        self._run_layout.addWidget(self.status_bar_chunks)

        self.but_close = QPushButton()
        self.but_close.clicked.connect(self.exit_procedure)
        self.but_close.setText('Cancel and close')
        self._run_layout.addWidget(self.but_close)

        self.setLayout(self._run_layout)
        self.resize(600, 135)

        self.run()

    def import_gtfs_process(self):
        self.resize_to_start_process()
        # new_name = GetOutputFolderName(self.path, 'Output folder for traffic assignment')
        # if new_name:
        #     self.output_path = new_name
        #     self.lbl_output.setText(new_name)
        # else:
        #     self.output_path = None
        #     self.lbl_output.setText(new_name)

    def run_thread(self):

        QObject.connect(self.worker_thread, SIGNAL("converting_gtfs"), self.signal_handler)
        self.worker_thread.start()
        self.exec_()

    def job_finished_from_thread(self):
        self.report = self.worker_thread.report
        self.produce_all_outputs()

        self.exit_procedure()


    def run(self):
        self.running = True
        self.worker_thread = gtfs_sqlite_db.load_from_zip()
        self.run_thread()

    def signal_handler(self, val):
        if val[0] == 'text':
            self.status_label_file.setText(val[1])

        elif val[0] == 'files counter':
            self.status_bar_files.setValue(val[1])

        elif val[0] == 'chunk counter':
            self.status_bar_chunks.setValue(val[1])

        elif val[0] == 'max chunk counter':
            self.status_bar_chunks.setMaximum(val[1])

        elif val[0] == 'finished_threaded_procedure':
            self.job_finished_from_thread()

    def exit_procedure(self):
        self.close()
        if self.running:
            self.worker_thread.stop()
        if self.report:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()

import sys
import logging
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtCore import *
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtWidgets import QRadioButton, QGridLayout, QPushButton, QHBoxLayout, QWidget, QLineEdit, QCheckBox
from qgis.PyQt.QtWidgets import QSpacerItem, QProgressBar, QLabel, QVBoxLayout, QSizePolicy, QCheckBox, QGroupBox
from qgis.PyQt.QtWidgets import QWidget, QFileDialog
import numpy as np

from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import *
from ..common_tools import ReportDialog, GetOutputFileName, standard_path
from aequilibrae.project import Project
from aequilibrae.project.network.osm_utils.place_getter import placegetter
from aequilibrae import Parameters

# from .osm_utils.osm_params import *
# from .osm_downloader import OSMDownloader

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class ProjectFromOSMDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.path = standard_path()
        self.error = None
        self.report = []
        self.worker_thread = None
        self.running = False
        self.bbox = None
        self.json = []
        self.project = None
        self.logger = logging.getLogger("aequilibrae")

        self._run_layout = QGridLayout()

        # Area to import network for
        self.choose_place = QRadioButton()
        self.choose_place.setText("Place name")
        self.choose_place.toggled.connect(self.change_place_type)
        self.choose_place.setChecked(False)

        self.choose_canvas = QRadioButton()
        self.choose_canvas.setText("Current map canvas area")
        self.choose_canvas.setChecked(True)

        self.place = QLineEdit()
        self.place.setVisible(False)

        self.source_type_frame = QVBoxLayout()
        self.source_type_frame.setAlignment(Qt.AlignLeft)
        self.source_type_frame.addWidget(self.choose_place)
        self.source_type_frame.addWidget(self.choose_canvas)
        self.source_type_frame.addWidget(self.place)

        self.source_type_widget = QGroupBox('Target')
        self.source_type_widget.setLayout(self.source_type_frame)

        # Buttons and output
        self.but_choose_output = QPushButton()
        self.but_choose_output.setText("Choose folder output")
        self.but_choose_output.clicked.connect(self.choose_output)

        self.output_path = QLineEdit()

        self.but_run = QPushButton()
        self.but_run.setText("Import network and create project")
        self.but_run.clicked.connect(self.run)

        self.buttons_frame = QVBoxLayout()
        self.buttons_frame.addWidget(self.but_choose_output)
        self.buttons_frame.addWidget(self.output_path)
        self.buttons_frame.addWidget(self.but_run)

        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_frame)

        self.progressbar = QProgressBar()
        self.progress_label = QLabel()

        self.update_widget = QWidget()
        self.update_frame = QVBoxLayout()
        self.update_frame.addWidget(self.progressbar)
        self.update_frame.addWidget(self.progress_label)
        self.update_widget.setLayout(self.update_frame)
        self.update_widget.setVisible(False)

        self._run_layout.addWidget(self.source_type_widget)
        self._run_layout.addWidget(self.buttons_widget)
        self._run_layout.addWidget(self.update_widget)

        self.setLayout(self._run_layout)
        self.resize(280, 250)

    def choose_output(self):
        new_name = QFileDialog.getExistingDirectory(QWidget(), "Parent folder", standard_path())
        if new_name is not None and len(new_name) > 0:
            self.output_path.setText(new_name)

    def run(self):
        self.update_widget.setVisible(True)
        self.resize(280, 300)
        if self.choose_canvas.isChecked():
            self.report.append(reporter('Chose to download network for canvas area'))
            e = self.iface.mapCanvas().extent()
            bbox = [e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum()]
        else:
            self.progress_label.setText('Establishing area for download')
            self.report.append(reporter('Chose to download network for place'))
            bbox, r = placegetter(self.place.text())
            self.report.extend(r)

        self.project = Project()
        self.project.new(self.output_path.text())
        self.project.network.netsignal.connect(self.signal_handler)
        self.project.network.create_from_osm(west=bbox[0], south=bbox[1], east=bbox[2], north=bbox[3])

    def change_place_type(self):
        if self.choose_place.isChecked():
            self.place.setVisible(True)
        else:
            self.place.setVisible(False)

    def leave(self):
        self.close()
        dlg2 = ReportDialog(self.iface, self.report)
        dlg2.show()
        dlg2.exec_()

    def signal_handler(self, val):
        if val[0] == "Value":
            self.progressbar.setValue(val[1])
        elif val[0] == "maxValue":
            self.progressbar.setRange(0, val[1])
        elif val[0] == "text":
            self.progress_label.setText(val[1])
        elif val[0] == "finished_threaded_procedure":
            l = self.project.network.count_links()
            n = self.project.network.count_nodes()
            self.report.append(reporter(f'{l:,} links generated'))
            self.report.append(reporter(f'{n:,} nodes generated'))
            self.leave()

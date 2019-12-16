import logging
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtCore import *
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtWidgets import QRadioButton, QGridLayout, QPushButton, QHBoxLayout, QWidget, QLineEdit, QCheckBox
from qgis.PyQt.QtWidgets import QSpacerItem, QProgressBar, QLabel, QVBoxLayout, QSizePolicy, QCheckBox, QGroupBox
from qgis.PyQt.QtWidgets import QWidget
import sys
from functools import partial
import numpy as np
from collections import OrderedDict

from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import *
from ..common_tools import ReportDialog, GetOutputFileName, standard_path
from .osm_utils.place_getter import placegetter

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

        # Modes to import
        self.chb_walk = QCheckBox()
        self.chb_walk.setText("Walking")
        self.chb_walk.setChecked(True)

        self.chb_bike = QCheckBox()
        self.chb_bike.setText("Cycling")
        self.chb_bike.setChecked(True)

        self.chb_motorized = QCheckBox()
        self.chb_motorized.setText("Motorized")
        self.chb_motorized.setChecked(True)

        self.modes_frame = QVBoxLayout()
        self.modes_frame.setAlignment(Qt.AlignLeft)
        self.modes_frame.addWidget(self.chb_walk)
        self.modes_frame.addWidget(self.chb_bike)
        self.modes_frame.addWidget(self.chb_motorized)

        self.modes_widget = QGroupBox('Modes')
        self.modes_widget.setLayout(self.modes_frame)

        # Fields to import
        self.all_fields = QVBoxLayout()

        self.chb_name = QCheckBox()
        self.chb_name.setText("Name")
        self.chb_name.setChecked(True)
        self.all_fields.addWidget(self.chb_name)

        self.chb_hierarchy = QCheckBox()
        self.chb_hierarchy.setText("Hierarchy")
        self.chb_hierarchy.setChecked(True)
        self.all_fields.addWidget(self.chb_hierarchy)

        self.chb_direction = QCheckBox()
        self.chb_direction.setText("Direction")
        self.chb_direction.setChecked(True)
        self.all_fields.addWidget(self.chb_direction)

        self.chb_lanes = QCheckBox()
        self.chb_lanes.setText("Lanes")
        self.chb_lanes.setChecked(True)
        self.all_fields.addWidget(self.chb_lanes)

        self.chb_speed = QCheckBox()
        self.chb_speed.setText("Speed")
        self.chb_speed.setChecked(True)
        self.all_fields.addWidget(self.chb_speed)

        self.chb_surface = QCheckBox()
        self.chb_surface.setText("Surface")
        self.chb_surface.setChecked(True)
        self.all_fields.addWidget(self.chb_surface)

        self.fields_widget = QGroupBox('Fields to import')
        self.fields_widget.setLayout(self.all_fields)

        # Buttons and output
        self.but_choose_output = QPushButton()
        self.but_choose_output.setText("Choose file output")
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

        self._run_layout.addWidget(self.source_type_widget)
        self._run_layout.addWidget(self.modes_widget)
        self._run_layout.addWidget(self.fields_widget)
        self._run_layout.addWidget(self.buttons_widget)

        self.setLayout(self._run_layout)
        self.resize(280, 400)

    def choose_output(self):
        new_name, file_type = GetOutputFileName(self, '', ["SQLite database(*.sqlite)"], ".sqlite", self.path)
        if new_name is not None:
            self.output_path.setText(new_name)

    def run(self):
        if self.choose_canvas.isChecked():
            self.report.append('Chose to download network for canvas area')
            e = self.iface.mapCanvas().extent()
            bbox = [e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum()]
        else:
            self.report.append('Chose to download network for place')
            bbox, r = placegetter(self.place.text())
            self.report.extend(r)

        if bbox is not None:
            self.report.append(
                'Downloading network for bounding box ({} {}, {}, {})'.format(bbox[0], bbox[1], bbox[2], bbox[3]))

        dlg2 = ReportDialog(self.iface, self.report)
        dlg2.show()
        dlg2.exec_()
            # geometry = feature.geometry()
            #
            # d = QgsDistanceArea()
            # d.convertAreaMeasurement(d.measureArea(geometry),QgsUnitTypes.AreaSquareMeters)

    def change_place_type(self):
        if self.choose_place.isChecked():
            self.place.setVisible(True)
        else:
            self.place.setVisible(False)

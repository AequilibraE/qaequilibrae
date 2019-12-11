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
from ..common_tools import ReportDialog, GetOutputFileName, GetOutputFolderName

from aequilibrae.transit.gtfs import create_gtfsdb

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))

# extent = iface.mapCanvas().extent()
# geometry = QgsGeometry().fromRect(extent)
#
# geometry = feature.geometry()
#
# d = QgsDistanceArea()
# d.convertAreaMeasurement(d.measureArea(geometry),QgsUnitTypes.AreaSquareMeters)


class ProjectFromOSMDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.path = standard_path()
        self.temp_path = None
        self.error = None
        self.report = None
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

        self.source_type_frame = QHBoxLayout()
        self.source_type_frame.setAlignment(Qt.AlignLeft)
        self.source_type_frame.addWidget(self.choose_place)
        self.source_type_frame.addWidget(self.choose_canvas)

        self.place_options = QWidget()
        self.place_options.setLayout(self.source_type_frame)

        self.complete_source = QVBoxLayout()
        self.complete_source.addWidget(self.place_options)
        self.complete_source.addWidget(self.place)

        self.source_type_widget = QGroupBox('Target')
        self.source_type_widget.setLayout(self.complete_source)

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

        self.modes_frame = QHBoxLayout()
        self.modes_frame.setAlignment(Qt.AlignLeft)
        self.modes_frame.addWidget(self.chb_walk)
        self.modes_frame.addWidget(self.chb_bike)
        self.modes_frame.addWidget(self.chb_motorized)

        self.modes_widget = QGroupBox('Modes')
        self.modes_widget.setLayout(self.modes_frame)

        # Fields to import
        self.chb_name = QCheckBox()
        self.chb_name.setText("Name")
        self.chb_name.setChecked(True)

        self.chb_hierarchy = QCheckBox()
        self.chb_hierarchy.setText("Hierarchy")
        self.chb_hierarchy.setChecked(True)

        self.chb_direction = QCheckBox()
        self.chb_direction.setText("Direction")
        self.chb_direction.setChecked(True)

        self.chb_lanes = QCheckBox()
        self.chb_lanes.setText("Lanes")
        self.chb_lanes.setChecked(True)

        self.chb_speed = QCheckBox()
        self.chb_speed.setText("Speed")
        self.chb_speed.setChecked(True)

        self.field_frame1 = QHBoxLayout()
        self.field_frame1.setAlignment(Qt.AlignLeft)
        self.field_frame1.addWidget(self.chb_name)
        self.field_frame1.addWidget(self.chb_lanes)
        self.field_frame1.addWidget(self.chb_speed)

        self.fieldw1 = QWidget()
        self.fieldw1.setLayout(self.field_frame1)

        self.field_frame2 = QHBoxLayout()
        self.field_frame2.setAlignment(Qt.AlignLeft)
        self.field_frame2.addWidget(self.chb_direction)
        self.field_frame2.addWidget(self.chb_hierarchy)

        self.fieldw2 = QWidget()
        self.fieldw2.setLayout(self.field_frame2)

        self.all_fields = QVBoxLayout()
        self.all_fields.addWidget(self.fieldw1)
        self.all_fields.addWidget(self.fieldw2)

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
        self.resize(300, 400)

    def choose_output(self):
        pass

    def run(self):
        pass

    def change_place_type(self):
        if self.choose_place.isChecked():
            self.place.setVisible(True)
        else:
            self.place.setVisible(False)
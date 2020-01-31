"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Main interface for adding centroid connectors
 Purpose:    Load GUI and user interface for the centroid addition procedure

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    2020-01-30
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from qgis.core import *
from qgis.PyQt.QtCore import *
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import *

from ..common_tools.auxiliary_functions import *
import sys
import os
from ..common_tools.global_parameters import *

from .adds_connectors_procedure import AddsConnectorsProcedure

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class AddConnectorsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, project):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.NewLinks = False
        self.NewNodes = False
        self.project = project
        if project is not None:
            self.conn = project.conn
            self.path_to_file = project.path_to_file

        self._run_layout = QGridLayout()
        spacer = QSpacerItem(5, 5, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Centroid layer
        frm1 = QHBoxLayout()
        frm1.addItem(spacer)
        self.CentroidLayer = QgsMapLayerComboBox()
        self.CentroidLayer.layerChanged.connect(self.set_fields)
        clabel = QLabel()
        clabel.setText("Centroids layer")
        frm1.addWidget(clabel)
        frm1.addWidget(self.CentroidLayer)
        self.CentroidLayer.setMinimumSize(450, 30)
        wdgt1 = QWidget()
        wdgt1.setLayout(frm1)

        self.CentroidField = QgsFieldComboBox()
        self.CentroidField.setMinimumSize(450, 30)
        frm2 = QHBoxLayout()
        frm2.addItem(spacer)
        flabel = QLabel()
        flabel.setText("Centroid ID field")
        frm2.addWidget(flabel)
        frm2.addWidget(self.CentroidField)
        wdgt2 = QWidget()
        wdgt2.setLayout(frm2)

        self.CentroidLayer.setFilters(QgsMapLayerProxyModel.PointLayer)

        frm3 = QHBoxLayout()
        self.IfMaxLength = QCheckBox()
        self.IfMaxLength.setChecked(True)
        self.IfMaxLength.setText("Connector maximum length")
        self.IfMaxLength.toggled.connect(self.allows_distance)
        frm3.addWidget(self.IfMaxLength)
        frm3.addItem(spacer)

        self.MaxLength = QLineEdit()
        frm3.addWidget(self.MaxLength)
        frm3.addItem(spacer)

        lblmeters = QLabel()
        lblmeters.setText(" meters")
        frm3.addWidget(lblmeters)
        frm3.addItem(spacer)

        lblnmbr = QLabel()
        lblnmbr.setText("Connectors per centroid")
        frm3.addWidget(lblnmbr)

        self.NumberConnectors = QComboBox()
        for i in range(1, 40):
            self.NumberConnectors.addItem(str(i))
        frm3.addWidget(self.NumberConnectors)

        wdgt3 = QWidget()
        wdgt3.setLayout(frm3)

        layer_frame = QVBoxLayout()
        layer_frame.addWidget(wdgt1)
        layer_frame.addWidget(wdgt2)
        layer_frame.addWidget(wdgt3)
        lyrfrm = QWidget()
        lyrfrm.setLayout(layer_frame)

        # action buttons
        self.but_process = QPushButton()
        if self.project is None:
            self.but_process.setText("Project not loaded")
            self.but_process.setEnabled(False)
        else:
            self.but_process.setText("Run!")
        self.but_process.clicked.connect(self.run)

        self.but_cancel = QPushButton()
        self.but_cancel.setText("Cancel")
        self.but_cancel.clicked.connect(self.exit_procedure)

        self.progressbar = QProgressBar()
        self.progress_label = QLabel()
        self.progress_label.setText("...")

        but_frame = QHBoxLayout()
        but_frame.addWidget(self.progressbar, 1)
        but_frame.addWidget(self.progress_label, 1)
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

        self._run_layout.addWidget(lyrfrm)
        self._run_layout.addWidget(self.but_widget)
        self._run_layout.addWidget(self.progress_widget)

        list = QWidget()
        listLayout = QVBoxLayout()
        self.list_types = QTableWidget()
        self.list_types.setMinimumSize(180, 80)

        lbl = QLabel()
        lbl.setText("Allowed link types")
        listLayout.addWidget(lbl)
        listLayout.addWidget(self.list_types)
        list.setLayout(listLayout)

        if self.project is not None:
            curr = self.conn.cursor()
            curr.execute("SELECT DISTINCT link_type FROM links ORDER BY link_type")
            ltypes = curr.fetchall()
            self.list_types.setRowCount(len(ltypes))
            self.list_types.setColumnCount(1)
            for i, lt in enumerate(ltypes):
                self.list_types.setItem(i, 0, QTableWidgetItem(lt[0]))
            self.list_types.selectAll()

        allStuff = QWidget()
        allStuff.setLayout(self._run_layout)
        allLayout = QHBoxLayout()
        allLayout.addWidget(allStuff)
        allLayout.addWidget(list)

        self.setLayout(allLayout)
        self.resize(700, 135)

        # default directory
        self.path = standard_path()
        self.set_fields()
        self.IfMaxLength.setChecked(False)

    def allows_distance(self):
        self.MaxLength.setEnabled(False)
        if self.IfMaxLength.isChecked():
            self.MaxLength.setEnabled(True)

    def run_thread(self):
        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressText.connect(self.progress_text_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.jobFinished.connect(self.job_finished_from_thread)
        self.worker_thread.start()
        self.show()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value)

    def set_fields(self):
        self.CentroidField.setLayer(self.CentroidLayer.currentLayer())

    def job_finished_from_thread(self, success):
        self.but_process.setEnabled(True)
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error during procedure: ", self.worker_thread.error, level=3)
        self.exit_procedure()

    def run(self):
        if self.MaxLength.isEnabled():
            max_length = float(self.MaxLength.text())
        else:
            max_length = 1000000000000
        self.link_types = []
        parameters = [self.project.path_to_file,
                      self.CentroidLayer.currentText(),
                      self.CentroidField.currentText(),
                      max_length,
                      int(self.NumberConnectors.currentText()),
                      self.link_types]

        self.but_process.setEnabled(False)
        self.worker_thread = AddsConnectorsProcedure(qgis.utils.iface.mainWindow(), *parameters)
        self.run_thread()

    def exit_procedure(self):
        self.close()

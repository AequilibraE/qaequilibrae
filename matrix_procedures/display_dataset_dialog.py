"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loads AequilibraE datasets for visualization
 Purpose:    Allows visual inspection of data

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-10-02
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import numpy as np


from ..common_tools import DatabaseModel
from ..aequilibrae.matrix import AequilibraEData
from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *
from ..common_tools.get_output_file_name import GetOutputFileName

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_data_viewer.ui'))

from PyQt4.QtGui import QHBoxLayout, QTableView, QTableWidget, QPushButton, QVBoxLayout
from PyQt4.QtGui import QComboBox, QCheckBox, QSpinBox, QWidget, QLabel, QSpacerItem


class DisplayDatasetDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, **kwargs):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.error = None
        self.data_path = None
        self.dataset = AequilibraEData()
        self.but_load.clicked.connect(self.load_the_vector)

    # Elements that will be used during the displaying
        self._layout = QVBoxLayout()
        self.table = QTableView()
        self._layout.addWidget(self.table)

        # Settings for displaying
        show_layout = QHBoxLayout()

            # Thousand separator
        self.thousand_separator = QCheckBox()
        self.thousand_separator.setChecked(True)
        self.thousand_separator.setText('Thousands separator')
        self.thousand_separator.toggled.connect(self.format_showing)
        show_layout.addWidget(self.thousand_separator)

        self.spacer = QSpacerItem(5, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        show_layout.addItem(self.spacer)

            # Decimals
        txt = QLabel()
        txt.setText('Decimal places')
        show_layout.addWidget(txt)
        self.decimals = QSpinBox()
        self.decimals.valueChanged.connect(self.format_showing)
        self.decimals.setMinimum(0)
        self.decimals.setValue(4)
        self.decimals.setMaximum(10)

        show_layout.addWidget(self.decimals)
        self._layout.addItem(show_layout)

        self.but_close = QPushButton()
        self.but_close.clicked.connect(self.format_showing)
        self.but_close.setText('Close')

        self._layout.addWidget(self.but_close)

    def load_the_vector(self):
        self.error = None
        self.data_path, _ = GetOutputFileName(self, 'AequilibraE dataset',
                                            ["Aequilibrae dataset(*.aed)"], '.aed', self.path)

        if self.data_path is None:
            self.error = 'No name provided for the output file'

        if self.error is None:
            try:
                self.but_load.setText('working...')
                self.but_load.setEnabled(False)
                self.dataset.load(self.data_path)
            except:
                self.error = 'Could not load dataset'

        if self.error is None:
            self.format_showing()
            self.but_load.setVisible(False)
        else:
            qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1)

    def format_showing(self):
        if self.dataset.entries is not None:
            decimals = self.decimals.value()
            separator = self.thousand_separator.isChecked()
            m = DatabaseModel(self.dataset, separator, decimals)
            self.table.clearSpans()
            self.table.setModel(m)

            # We chose to use QTableView. However, if we want to allow the user to edit the dataset
            # The we need to allow them to switch to the slower QTableWidget
            # Code below

            # self.table = QTableWidget(self.dataset.entries, self.dataset.num_fields)
            # self.table.setHorizontalHeaderLabels(self.dataset.fields)
            # self.table.setObjectName('data_viewer')
            #
            # self.table.setVerticalHeaderLabels([str(x) for x in self.dataset.index[:]])
            # self.table.clearContents()
            #
            # for i in range(self.dataset.entries):
            #     for j, f in enumerate(self.dataset.fields):
            #         item1 = QTableWidgetItem(str(self.dataset.data[f][i]))
            #         item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            #         self.table.setItem(i, j, item1)

            self.setLayout(self._layout)
            self.resize(700, 500)

    def exit_procedure(self):
        self.close()

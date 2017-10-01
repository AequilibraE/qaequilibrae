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

 Created:    2017-10-30
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

from PyQt4.QtGui import  QHBoxLayout, QTableView, QTableWidget
class DisplayVectorDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, **kwargs):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.error = None
        self.data_path = None
        self.dataset = AequilibraEData()
        self.but_load.clicked.connect(self.load_the_vector)

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

                self.table = QTableView()
                m = DatabaseModel(self.dataset)
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

                self.but_load.setVisible(False)
                self.h_layout = QHBoxLayout()
                self.h_layout.addWidget(self.table)
                self.setLayout(self.h_layout)
                self.resize(700, 500)

            except:
                self.error = 'Could not load dataset'

        if self.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1)

    def exit_procedure(self):
        self.close()

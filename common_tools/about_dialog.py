"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       About dialog
 Purpose:    Dialog for showing the About window

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-12-16
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *

import sys
import os
from auxiliary_functions import standard_path
from ..aequilibrae.__version__ import release_name, release_version

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_about.ui'))

class AboutDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.but_mailing.clicked.connect(self.go_to_mailing_list)
        self.but_close.clicked.connect(self.exit_procedure)

        # self.developers = ['Pedro Camargo', 'Jamie Cook (MacOS binaries)']
        self.developers = 'Pedro Camargo, Jamie Cook (MacOS binaries)'
        # self.sponsors = ['IPEA (2015)']
        self.sponsors = 'IPEA (2015)'

        self.all_items = []
        self.all_items.append(['Version name', release_name])
        self.all_items.append(['Version number', release_version])
        self.all_items.append(['Minimum QGIS', '2.16'])
        self.all_items.append(['Developers', self.developers])
        self.all_items.append(['Sponsors', self.sponsors])

        self.assemble()

    def assemble(self):
        titles = []
        currentRowCount = 0
        for r, t in self.all_items:
            titles.append(r)
            self.about_table.insertRow(currentRowCount)

            # if isinstance(t, list):
            #     tbl = QtGui.QTableWidget(len(t),1)
            #     for i, item in enumerate(t):
            #         tbl.setItem(i,0, QTableWidgetItem(item))
            #     self.about_table.setCellWidget(currentRowCount, 0, tbl)
            # else:
            self.about_table.setItem(currentRowCount, 0, QTableWidgetItem(str(t)))
            currentRowCount += 1

        self.about_table.setVerticalHeaderLabels(titles)
    def go_to_mailing_list(self):


        self.exit_procedure()

    def exit_procedure(self):
        self.close()

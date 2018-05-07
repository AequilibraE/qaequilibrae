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

from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
import webbrowser

import os
from auxiliary_functions import standard_path
from ..aequilibrae.paths import release_name, release_version

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_about.ui'))


class AboutDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.but_mailing.clicked.connect(self.go_to_mailing_list)
        self.but_close.clicked.connect(self.exit_procedure)

        repository = 'https://github.com/AequilibraE/AequilibraE'
        self.wiki = "https://github.com/aequilibrae/aequilibrae/wiki"
        sponsors = ['IPEA (2015)']
        developers = ['Pedro Camargo','Yu-Chu Huang' ,'Jamie Cook (MacOS binaries)']

        self.all_items = []
        self.all_items.append(['Version name', release_name])
        self.all_items.append(['Version number', release_version])
        self.all_items.append(['Repository', repository])
        self.all_items.append(['Minimum QGIS', '2.16'])
        self.all_items.append(['Developers', developers])
        self.all_items.append(['Sponsors', sponsors])

        self.assemble()

    def assemble(self):
        titles = []
        row_count = 0

        for r, t in self.all_items:
            titles.append(r)
            self.about_table.insertRow(row_count)
            if isinstance(t, list):
                lv = QListWidget()
                lv.addItems(t)
                self.about_table.setCellWidget(row_count, 0, lv)
                self.about_table.setRowHeight(row_count, len(t)*self.about_table.rowHeight(row_count))
            else:
                self.about_table.setItem(row_count, 0, QTableWidgetItem(str(t)))

            row_count += 1
        self.about_table.setVerticalHeaderLabels(titles)

    def go_to_mailing_list(self):
        webbrowser.open(self.wiki, new=2)
        self.exit_procedure()

    def exit_procedure(self):
        self.close()

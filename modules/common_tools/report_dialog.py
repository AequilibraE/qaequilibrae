"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Report dialog
 Purpose:    Dialog for showing the report from algorithm runs

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
 Updated:    2018-07-01
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from qgis.PyQt import QtWidgets, uic
from .get_output_file_name import GetOutputFileName
import qgis

import sys
import os
from .auxiliary_functions import standard_path

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_report.ui"))


class ReportDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, reporting):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.reporting = reporting
        for t in reporting:
            self.all_data.append(t)

        self.but_save_log.clicked.connect(self.save_log)
        self.but_close.clicked.connect(self.exit_procedure)

    def save_log(self):
        file_types = "Text files(*.txt)"
        new_name, _ = GetOutputFileName(self, "Save procedure log", file_types, ".txt", self.path)
        if new_name is not None:
            with open(new_name, "w") as outp:
                for t in self.reporting:
                    outp.write(t)
            self.exit_procedure()

    def exit_procedure(self):
        self.close()

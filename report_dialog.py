"""
/***************************************************************************
 AequilibraE - www.AequilibraE.com

    Name:        Dialog for showing the report from algorithm runs
                              -------------------
        Creation           2016-29-16
        Update             2016-29-16
        copyright            : AequilibraE developers 2016
        Original Author: Pedro Camargo (c@margo.co)
        Contributors:
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""

from qgis.core import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

import sys
import os
from auxiliary_functions import standard_path

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/")

from ui_report import Ui_report

class ReportDialog(QtGui.QDialog, Ui_report):
    def __init__(self, iface, reporting):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.reporting = reporting
        for t in reporting:
            self.all_data.append(t)

        self.but_save_log.clicked.connect(self.save_log)

    def save_log(self):
        file_types = "Text files(*.txt)"
        newname = QFileDialog.getSaveFileName(None, 'Save log', self.path, file_types)
        if newname is not None:
            outp = open(newname, 'w')
            for t in self.reporting:
                print >> outp, t
            outp.flush()
            outp.close()
            self.ExitProcedure()

    def ExitProcedure(self):
        self.close()

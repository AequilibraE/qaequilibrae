"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Iterative proportinal fitting
 Purpose:    Loads GUI for applying proportinal fitting

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-09-29
 Updated:    2016-10-03
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) + "//forms//")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

from qgis.core import *
import qgis
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from functools import partial
import numpy as np
import warnings

from auxiliary_functions import *
from load_matrix_dialog import LoadMatrixDialog
from load_vector_dialog import LoadVectorDialog
from report_dialog import ReportDialog

from ipf_procedure import IpfProcedure
from ui_ipf import Ui_ipf

try:
    import omx
    OMX = True
except:
    OMX = False

warnings.filterwarnings('ignore')

class IpfDialog(QDialog, Ui_ipf):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.error = None
        self.outname = None
        self.report = None

        self.path = standard_path()

        # Hide the progress bars
        self.progressbar.setVisible(False)
        self.progress_label.setVisible(False)
        self.progressbar.setValue(0)
        self.progress_label.setText('')

        # FIRST, we connect slot signals
        # For changing the input matrix
        self.but_load_new_matrix.clicked.connect(self.find_matrices)
        self.but_load_rows.clicked.connect(partial(self.find_vectors, 'rows'))
        self.but_load_columns.clicked.connect(partial(self.find_vectors, 'columns'))

        self.but_choose_output_name.clicked.connect(self.browse_outfile)

    # Create desire lines
        self.apply_ipf.clicked.connect(self.run)

    def browse_outfile(self):
        file_types = "Comma-separated files(*.csv);;Numpy Binnary Array(*.npy)"
        if OMX:
            file_types += ";;OpenMatrix(*.omx)"
        new_name = QFileDialog.getSaveFileName(None, 'Result matrix', self.path, file_types)
        if new_name is not None:
            self.outname = new_name
            self.output_name.setText(new_name)

    def run_thread(self):
        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.job_finished_from_thread)
        self.worker_thread.start()
        self.exec_()

    def find_matrices(self):
        dlg2 = LoadMatrixDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.matrix is not None:
            self.matrix = dlg2.matrix
            self.matrix_name.setText('LOADED')
            self.matrix_total.setText("{:20,.4f}".format(np.sum(self.matrix)))

    def find_vectors(self, destination):
        dlg2 = LoadVectorDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.vector is not None:
            if destination == 'rows':
                self.rows = dlg2.vector
                self.rows_name.setText('LOADED')
                self.rows_total.setText("{:20,.4f}".format(np.sum(self.rows)))
            else:
                self.columns = dlg2.vector
                self.columns_name.setText('LOADED')
                self.columns_total.setText("{:20,.4f}".format(np.sum(self.columns)))

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val[1])

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value[1])

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value[1])

    def job_finished_from_thread(self, success):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Procedure error: ", self.worker_thread.error, level=3)
        else:
            self.output = self.worker_thread.ipf.output
            self.report = self.worker_thread.ipf.report

            if self.outname[-3:].upper() == 'NPY':
                np.save(self.outname, self.output)
            else:
                outp = open(self.outname, 'w')
                print >> outp, 'O,D,Flow'
                print_zeros = get_parameter_chain(['system', 'report zeros'])
                if print_zeros:
                    for i in range(self.output.shape[0]):
                        for j in range(self.output.shape[1]):
                            print >> outp, str(i) + ',' + str(j) + ',' + str(self.output[i, j])
                else:
                    for i in range(self.output.shape[0]):
                        for j in range(self.output.shape[1]):
                            if self.output[i, j]:
                                print >> outp, str(i) + ',' + str(j) + ',' + str(self.output[i, j])
                    outp.flush()
                    outp.close()
        self.exit_procedure()

    def run(self):
        if self.matrix is not None and self.rows is not None and self.columns is not None:
            self.worker_thread = IpfProcedure(qgis.utils.iface.mainWindow(), self.matrix, self.rows, self.columns)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Matrix not loaded", '', level=3)

    def exit_procedure(self):
        self.close()
        dlg2 = ReportDialog(self.iface, self.report)
        dlg2.show()
        dlg2.exec_()




"""
/***************************************************************************
 AequilibraE - www.AequilibraE.com
 
    Name:        Dialogs for applying proportinal fitting
                              -------------------
        begin                : 2016-09-29
        copyright            : TOOLS developers 2014
        Original Author: Pedro Camargo pedro@xl-optim.com
        Contributors: 
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""

from qgis.core import *
import qgis
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
from functools import partial
import numpy as np

from auxiliary_functions import *
from load_matrix_dialog import LoadMatrixDialog
from load_vector_dialog import LoadVectorDialog

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "//forms//")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "//algorithms//")

from ipf_procedure import IpfProcedure
from ui_ipf import Ui_ipf

try:
    import omx
    OMX = True
except:
    OMX = False

class IpfDialog(QDialog, Ui_ipf):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.error = None
        self.outname = None

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
        newname = QFileDialog.getSaveFileName(None, 'Result matrix', self.path, file_types)
        if newname is not None:
            self.output_name.setText(newname)
            self.outname = newname

    def runThread(self):
        QObject.connect(self.workerThread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.ProgressValueFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressText( PyQt_PyObject )"), self.ProgressTextFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.ProgressRangeFromThread)
        QObject.connect(self.workerThread, SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"),
                        self.jobFinishedFromThread)
        self.workerThread.start()
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

    def ProgressRangeFromThread(self, val):
        self.progressbar.setRange(0, val[1])

    def ProgressValueFromThread(self, value):
        self.progressbar.setValue(value[1])

    def ProgressTextFromThread(self, value):
        self.progress_label.setText(value[1])

    def jobFinishedFromThread(self, success):
        if self.workerThread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Procedure error: ", self.workerThread.error, level=3)
        else:
            self.output = self.workerThread.ipf.output
            np.save(self.outname, self.output)
        self.ExitProcedure()

    def run(self):
        if None not in [self.matrix, self.rows, self.columns]:
            self.workerThread = IpfProcedure(qgis.utils.iface.mainWindow(), self.matrix, self.rows, self.columns)
            self.runThread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Matrix not loaded", '', level=3)

    def ExitProcedure(self):
        self.close()

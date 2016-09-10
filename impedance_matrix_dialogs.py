"""
/***************************************************************************
 AequilibraE - www.AequilibraE.com
 
    Name:        Dialogs for modeling tools
                              -------------------
        begin                : 2014-03-19
        copyright            : TOOLS developers 2014
        Original Author: Pedro Camargo pedro@xl-optim.com
        Contributors: 
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""

from qgis.core import *
import qgis
from PyQt4 import QtGui
from PyQt4.QtGui import *
from PyQt4.QtCore import QObject, SIGNAL
import sys, os
import numpy as np
from functools import partial

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/")
from impedance_matrix_procedures import ComputeDistMatrix
from aequilibrae.paths import Graph
from aequilibrae.paths.results import PathResults

from auxiliary_functions import *
from global_parameters import *
from ui_impedance_matrix import *


class ImpedanceMatrixDialog(QtGui.QDialog, Ui_Impedance_Matrix):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.result = PathResults()
        self.validtypes = integer_types + float_types
        self.tot_skims = 0
        self.name_skims = 0
        self.skimmeable_fields = []
        self.skim_fields = []
        # FIRST, we connect slot signals

        #For loading a new graph
        self.load_graph_from_file.clicked.connect(self.loaded_new_graph_from_file)

        # For adding skims
        self.bt_add_skim.clicked.connect(self.add_to_skim_list)
        self.skim_list.doubleClicked.connect(self.slotDoubleClicked)

        # RUN skims
        self.select_result.clicked.connect(self.browse_outfile)

        self.do_dist_matrix.clicked.connect(self.run_skimming)


        # SECOND, we set visibility for sections that should not be shown when the form opens (overlapping items)
        #        and re-dimension the items that need re-dimensioning
        self.HideAllProgressBars()
        self.skim_list.setColumnWidth(0, 567)

        # loads default path from parameters
        self.path = standard_path()


    def HideAllProgressBars(self):
        self.progressbar.setVisible(False)
        self.progress_label.setVisible(False)
        self.progressbar.setValue(0)
        self.progress_label.setText('')

    def loaded_new_graph_from_file(self):
        file_types = "AequilibraE graph(*.aeg)"
        if len(self.graph_file_name.text()) > 0:
            newname = QFileDialog.getOpenFileName(None, 'Result file', self.graph_file_name.text(), file_types)
        else:
            newname = QFileDialog.getOpenFileName(None, 'Result file', self.path, file_types)

        self.cb_minimizing.clear()
        self.cb_skims.clear()
        self.all_centroids.setText('')
        self.block_paths.setChecked(False)
        if newname is not None:
            self.graph_file_name.setText(newname)
            self.graph = Graph()
            self.graph.load_from_disk(newname)

            self.all_centroids.setText(str(self.graph.centroids))
            if self.graph.block_centroid_flows:
                self.block_paths.setChecked(True)
            graph_fields = list(self.graph.graph.dtype.names)
            self.skimmeable_fields = [x for x in graph_fields if x not in ['link_id', 'a_node', 'b_node', 'direction', 'id',]]

            for q in self.skimmeable_fields:
                self.cb_minimizing.addItem(q)
                self.cb_skims.addItem(q)

    def add_to_skim_list(self):
        if self.cb_skims.currentIndex()>=0:
            self.tot_skims += 1
            self.skim_list.setRowCount(self.tot_skims)
            self.skim_list.setItem(self.tot_skims - 1, 0, QtGui.QTableWidgetItem((self.cb_skims.currentText())))
            self.skim_fields.append(self.cb_skims.currentText())
            self.cb_skims.removeItem(self.cb_skims.currentIndex())

    def slotDoubleClicked(self, mi):
        row = mi.row()
        if row > -1:
            self.cb_skims.addItem(self.skim_list.item(row,0).text())
            self.skim_fields.pop(row)
            self.skim_list.removeRow(row)
            self.tot_skims -= 1

    def browse_outfile(self):
        file_types = "Comma-Separated files(*.csv)"
        if self.npy_res.isChecked():
            file_types = "Numpy Binnary Array(*.npy)"

        if len(self.imped_results.text()) > 0:
            newname = QFileDialog.getSaveFileName(None, 'Result file', self.imped_results.text(), file_types)
        else:
            newname = QFileDialog.getSaveFileName(None, 'Result file', self.path, file_types)

        self.imped_results.setText('')
        if newname != None:
            self.imped_results.setText(newname)

    def runThread(self):

        QObject.connect(self.workerThread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.ProgressValueFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressText( PyQt_PyObject )"), self.ProgressTextFromThread)
        QObject.connect(self.workerThread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.ProgressRangeFromThread)

        QObject.connect(self.workerThread, SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"),
                        self.FinishedThreadedProcedure)

        self.workerThread.start()
        self.exec_()

    # VAL and VALUE have the following structure: (bar/text ID, value)
    def ProgressRangeFromThread(self, val):
        self.progressbar.setRange(0, val[1])

    def ProgressValueFromThread(self, val):
        self.progressbar.setValue(val[1])

    def ProgressTextFromThread(self, val):
        self.progress_label.setText(val[1])

    def FinishedThreadedProcedure(self, val):
        if self.workerThread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Assignment did NOT run correctly", self.workerThread.error, level=3)
        else:
            mat = self.workerThread.skim_matrices
            mat[mat > 1e308] = np.inf # We treat the "infinity" that should have been treated within the Cython code

            if self.npy_res.isChecked():
                np.save(self.imped_results.text(), mat)
                q = open(self.imped_results.text()+'.csv', 'w')
                for l in self.skim_fields:
                    print >> q, l
                q.flush()
                q.close()
            if self.csv_res.isChecked():
                q = open(self.imped_results.text(), 'w')
                text = 'Origin,Destination,' + self.cb_minimizing.currentText()
                for l in self.skim_fields:
                    text = text + ',' + l
                print >> q, text
                for i in range(mat.shape[0]):
                    if np.sum(mat[i,:,:])>0:
                        for j in range(mat.shape[1]):
                            if np.sum(mat[i,j,:])>0:
                                text = str(i) + ',' + str(j)
                                s = 0
                                for k in range(mat.shape[2]):
                                    if mat[i,j,k] != np.inf:
                                        s += mat[i,j,k]
                                        text = text + ',' + str(mat[i,j,k])
                                    else:
                                        text += ','
                                if s>0:
                                    print >>q, text
                    q.flush()
                q.close()
        self.close()

    def run_skimming(self):  # Saving results
        centroids = int(self.all_centroids.text())
        cost_field = self.cb_minimizing.currentText()
        block_paths = False
        if self.block_paths.isChecked():
            block_paths = True

        if centroids > 0:
            self.graph.set_graph(centroids, cost_field, self.skim_fields, block_paths)
            self.result.prepare(self.graph)
        else:
            qgis.utils.iface.messageBar().pushMessage("Nothing to run.", 'Number of centroids set to zero', level=3)

        if len(self.imped_results.text()) == 0:
            qgis.utils.iface.messageBar().pushMessage("Cannot run.", 'No output file provided', level=3)
        else:
            self.funding1.setVisible(False)
            self.funding2.setVisible(False)
            self.progressbar.setVisible(True)
            self.progress_label.setVisible(True)
            self.workerThread = ComputeDistMatrix(qgis.utils.iface.mainWindow(),  self.graph, self.result)
            self.runThread()


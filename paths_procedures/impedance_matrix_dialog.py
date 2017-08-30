"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Creating impedance matrices
 Purpose:    Loads GUI to create impedance matrices

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import QObject, SIGNAL
import sys, os
import numpy as np

from impedance_matrix_procedures import ComputeDistMatrix
from aequilibrae.paths import Graph
from aequilibrae.paths import SkimResults
from ..common_tools import GetOutputFileName
from ..common_tools import ReportDialog
from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *

#sys.modules['qgsmaplayercombobox'] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_impedance_matrix.ui'))


class ImpedanceMatrixDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.result = SkimResults()
        self.validtypes = integer_types + float_types
        self.tot_skims = 0
        self.name_skims = 0
        self.skimmeable_fields = []
        self.skim_fields = []
        # FIRST, we connect slot signals

        # For loading a new graph
        self.load_graph_from_file.clicked.connect(self.loaded_new_graph_from_file)

        # For adding skims
        self.bt_add_skim.clicked.connect(self.add_to_skim_list)
        self.skim_list.doubleClicked.connect(self.slot_double_clicked)

        # RUN skims
        self.select_result.clicked.connect(self.browse_outfile)

        self.do_dist_matrix.clicked.connect(self.run_skimming)

        # SECOND, we set visibility for sections that should not be shown when the form opens (overlapping items)
        #        and re-dimension the items that need re-dimensioning
        self.hide_all_progress_bars()
        self.skim_list.setColumnWidth(0, 567)

        # loads default path from parameters
        self.path = standard_path()

    def hide_all_progress_bars(self):
        self.progressbar.setVisible(False)
        self.progress_label.setVisible(False)
        self.progressbar.setValue(0)
        self.progress_label.setText('')

    def loaded_new_graph_from_file(self):
        file_types = ["AequilibraE graph(*.aeg)"]

        new_name, file_type = GetOutputFileName(self, 'Graph file', file_types, ".aeg", self.path)
        self.cb_minimizing.clear()
        self.cb_skims.clear()
        self.all_centroids.setText('')
        self.block_paths.setChecked(False)
        if new_name is not None:
            self.graph_file_name.setText(new_name)
            self.graph = Graph()
            self.graph.load_from_disk(new_name)

            self.all_centroids.setText(str(self.graph.centroids))
            if self.graph.block_centroid_flows:
                self.block_paths.setChecked(True)
            graph_fields = list(self.graph.graph.dtype.names)
            self.skimmeable_fields = [x for x in graph_fields if
                                      x not in ['link_id', 'a_node', 'b_node', 'direction', 'id', ]]

            for q in self.skimmeable_fields:
                self.cb_minimizing.addItem(q)
                self.cb_skims.addItem(q)

    def add_to_skim_list(self):
        if self.cb_skims.currentIndex() >= 0:
            self.tot_skims += 1
            self.skim_list.setRowCount(self.tot_skims)
            self.skim_list.setItem(self.tot_skims - 1, 0, QtGui.QTableWidgetItem((self.cb_skims.currentText())))
            self.skim_fields.append(self.cb_skims.currentText())
            self.cb_skims.removeItem(self.cb_skims.currentIndex())

    def slot_double_clicked(self, mi):
        row = mi.row()
        if row > -1:
            self.cb_skims.addItem(self.skim_list.item(row, 0).text())
            self.skim_fields.pop(row)
            self.skim_list.removeRow(row)
            self.tot_skims -= 1

    def browse_outfile(self):
        file_types = "Comma-Separated files(*.csv)"
        def_type='.csv'
        if self.radio_aequilibrae.isChecked():
            file_types = "AequilibraE Array(*.aem)"
            def_type = 'aem'

        new_name, _ = GetOutputFileName(self, 'AequilibraE impedance computation', [file_types], def_type, self.path)

        self.imped_results.setText('')
        if new_name is not None:
            self.imped_results.setText(new_name)

    def run_thread(self):

        self.do_dist_matrix.setVisible(False)
        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"),
                        self.progress_range_from_thread)

        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.finished_threaded_procedure)

        self.worker_thread.start()
        self.exec_()

    # VAL and VALUE have the following structure: (bar/text ID, value)
    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, val):
        self.progressbar.setValue(val)

    def progress_text_from_thread(self, val):
        self.progress_label.setText(val)

    def finished_threaded_procedure(self, val):
        if len(self.worker_thread.report) > 0:
            self.report = self.worker_thread.report

        if self.radio_aequilibrae.isChecked():
            self.result.skims.save_to_disk(file_path=self.imped_results.text(), compressed=True)
        if self.radio_csv.isChecked():
            self.result.skims.export(self.imped_results.text())
        self.exit_procedure()

    def run_skimming(self):  # Saving results
        centroids = int(self.all_centroids.text())
        cost_field = self.cb_minimizing.currentText()
        block_paths = False
        if self.block_paths.isChecked():
            block_paths = True

        if centroids > 0:
            # Guarantees that there is only one copy of the minimizing value in there
            if cost_field in self.skim_fields:
                self.skim_fields.remove(cost_field)

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
            self.worker_thread = ComputeDistMatrix(qgis.utils.iface.mainWindow(), self.graph, self.result)
            self.run_thread()

    def exit_procedure(self):
        self.close()
        if self.report:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()
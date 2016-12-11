"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Traffic assignment
 Purpose:    Loads GUI to perform traffic assignment procedures

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-10-30
 Updated:...
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, QtCore
from qgis.gui import QgsMapLayerProxyModel, QgsFieldProxyModel
import sys
import os
from functools import partial
import numpy as np
import uuid
import shutil

from global_parameters import integer_types
from auxiliary_functions import *
from load_matrix_dialog import LoadMatrixDialog
from report_dialog import ReportDialog
from numpy_model import NumpyModel
from ui_traffic_assignment import Ui_traffic_assignment
from traffic_assignment_procedure import TrafficAssignmentProcedure
from aequilibrae.paths import Graph, AssignmentResults
from get_output_file_name import GetOutputFileName


class TrafficAssignmentDialog(QDialog, Ui_traffic_assignment):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.temp_path = tempPath() + '/'

        self.error = None
        self.outname = None
        self.output = None
        self.report = None
        self.method = {}

        self.matrix = None
        self.graph = Graph()
        self.results = AssignmentResults()

        # Signals for the matrix tab
        self.but_load_new_matrix.clicked.connect(self.find_matrices)
        self.display_matrix.stateChanged.connect(self.display_matrix_or_not)

        # Signals from the Network tab
        self.load_graph_from_file.clicked.connect(self.load_graph)
        self.network_layer.setVisible(False)
        self.network_field.setVisible(False)
        self.lblnodematch_11.setVisible(False)
        self.lblnodematch_14.setVisible(False)
        self.chb_check_consistency.setVisible(False)
        self.network_layer.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.network_layer.layerChanged.connect(self.add_fields_to_cboxes)
        self.add_fields_to_cboxes()

        # Signals for the algorithm tab
        self.progressbar0.setVisible(False)
        self.progressbar0.setValue(0)
        self.progress_label0.setVisible(False)

        self.do_assignment.clicked.connect(self.run)
        self.cancel_all.clicked.connect(self.exit_procedure)
        self.select_result.clicked.connect(self.browse_outfile)

        self.cb_choose_algorithm.addItem('All-Or-Nothing')
        self.cb_choose_algorithm.currentIndexChanged.connect(self.changing_algorithm)

        # slots for skim tab
        self.add_skim.clicked.connect(self.select_skim)

        self.changing_algorithm()

        # critical analysis and path file saving
        self.group_outputs = False
        self.do_group_outputs.setEnabled(False)
        self.do_path_file.stateChanged.connect(self.change_status_for_path_file)
        self.select_path_file_name.clicked.connect(self.choose_output_for_path_file)
        self.do_path_file.setEnabled(False)
        self.change_status_for_path_file()
        self.path_file_output_name = None
        self.temp_path_file = None

    def choose_output_for_path_file(self):
        new_name, type = GetOutputFileName(self, 'Path File', ["AequilibraE Path File(*.aep)"], ".aep", self.path)

        if new_name is not None:
            self.path_file_output_name = new_name
            self.path_file_display.setText(new_name)
            self.temp_path_file = self.temp_path + uuid.uuid4().hex
            self.results.setSavePathFile(True, self.temp_path_file + '.aep')
        else:
            self.path_file_output_name = None
            self.path_file_display.setText('...')

    def change_status_for_path_file(self):
        if self.do_path_file.isChecked():
            self.select_path_file_name.setEnabled(True)
            self.path_file_display.setVisible(True)
        else:
            self.select_path_file_name.setEnabled(False)
            self.path_file_display.setVisible(False)
            self.path_file_output_name = None
            self.path_file_display.setText('...')

    def select_skim(self):
        pass

    def load_graph(self):
        self.lbl_graphfile.setText('')

        file_types = ["AequilibraE graph(*.aeg)"]
        default_type = '.aeg'
        box_name = 'Traffic Assignment'
        graph_file, type = GetOutputFileName(self, box_name, file_types, default_type, self.path)

        if graph_file is not None:
            self.graph.load_from_disk(graph_file)

            not_considering_list = self.graph.required_default_fields
            not_considering_list.pop(-1)
            not_considering_list.append('id')

            for i in list(self.graph.graph.dtype.names):
                if i not in not_considering_list:
                    self.minimizing_field.addItem(i)
            self.lbl_graphfile.setText(graph_file)
            self.results.prepare(self.graph)
            cores = get_parameter_chain(['system', 'cpus'])
            self.results.set_cores(cores)

            self.do_path_file.setEnabled(True)

        else:
            self.graph = Graph()
            self.do_path_file.setEnabled(False)
        self.change_status_for_path_file()

    def browse_outfile(self):
        file_types = ["Comma-separated files(*.csv)", "Numpy Binnary Array(*.npy)"]
        default_type = '.csv'
        box_name = 'Result Matrix'
        new_name, type = GetOutputFileName(self, box_name, file_types, default_type, self.path)

        if len(new_name) > 0:
            self.outname = new_name
            self.lbl_output.setText(self.outname)
        else:
            self.outname = None
            self.lbl_output.setText('')

    def add_fields_to_cboxes(self):
        l = get_vector_layer_by_name(self.network_layer.currentText())
        if l is not None:
            self.layer = l
            self.network_field.clear()
            for field in self.layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    self.network_field.addItem(field.name())

    def changing_algorithm(self):
        pass
        if self.cb_choose_algorithm.currentText() == 'All-Or-Nothing':
            self.method['algorithm'] = 'AoN'

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
            self.display_matrix_or_not()
        else:
            self.matrix = None

    def display_matrix_or_not(self):
        if self.display_matrix.isChecked() and self.matrix is not None:
            row_headers = []
            col_headers = []
            for i in range(self.matrix.shape[0]):
                row_headers.append(str(i))

            for j in range(self.matrix.shape[1]):
                col_headers.append(str(j))

            m = NumpyModel(self.matrix, col_headers, row_headers)
            self.matrix_viewer.setModel(m)
        else:
            self.matrix_viewer.clearSpans()


    def job_finished_from_thread(self, success):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Procedure error: ", self.worker_thread.error, level=3)
        else:
            self.output = self.results.results()
            self.report = self.worker_thread.report

            if self.outname[-3:].upper() == 'NPY':
                np.save(self.outname, self.output)

            else:
                self.produce_all_outputs()

    def run(self):
        if self.check_data():
            self.progressbar0.setVisible(True)
            self.worker_thread = TrafficAssignmentProcedure(qgis.utils.iface.mainWindow(), self.matrix, self.graph,
                                                       self.results, self.method)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input error", self.error, level=3)

    def check_data(self):
        self.error = None

        if self.matrix is None:
            self.error = 'Demand matrix missing'

        if not self.graph.num_links:
            self.error = 'Graph was not loaded'

        # if not len(self.network_layer.currentText()):
        #     self.error = 'No line layer selected'

        # if not len(self.network_field.currentText()):
        #     self.error = 'No link ID field selected'

        if self.outname is None:
            self.error = 'Parameters for output missing'

        if self.do_path_file.isChecked() and self.path_file_output_name is None:
            self.error = 'No output file name for the path file selected'

        if self.error is not None:
            return False
        else:
            return True

    def progress_range_from_thread(self, val):
        self.progressbar0.setRange(0, val)

    def progress_value_from_thread(self, val):
        self.progressbar0.setValue(val)

    def progress_text_from_thread(self, val):
        self.progress_label0.setText(val)

    def produce_all_outputs(self):

        # Save link flows to disk
        self.results.save_loads_to_disk(self.outname)

        if self.do_path_file.isChecked():
            if self.method['algorithm'] == 'AoN':
                del(self.results.path_file['results'])
                self.results.path_file = None

                shutil.move(self.temp_path_file + '.aep', self.path_file_output_name)
                shutil.move(self.temp_path_file + '.aed', self.path_file_output_name[:-3] + 'aed')


        self.exit_procedure()
        #+ '.aep'

    def exit_procedure(self):
        self.close()
        if len(self.report) > 0:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()




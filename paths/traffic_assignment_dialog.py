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
 Updated:
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
import yaml



from global_parameters import integer_types
from auxiliary_functions import *
from load_matrix_dialog import LoadMatrixDialog
from report_dialog import ReportDialog
from numpy_model import NumpyModel
from ui_traffic_assignment import Ui_traffic_assignment
from traffic_assignment_procedure import TrafficAssignmentProcedure
from aequilibrae.paths import Graph, AssignmentResults



class TrafficAssignmentDialog(QDialog, Ui_traffic_assignment):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

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
        self.network_layer.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.network_layer.layerChanged.connect(self.add_fields_to_cboxes)
        self.add_fields_to_cboxes()

        # Signals for the algorithm tab
        self.progressbar0.setVisible(False)
        self.progressbar0.setValue(0)

        self.do_assignment.clicked.connect(self.run)
        self.cancel_all.clicked.connect(self.exit_procedure)
        self.select_result.clicked.connect(self.browse_outfile)

        self.cb_choose_algorithm.addItem('All-Or-Nothing')
        self.cb_choose_algorithm.currentIndexChanged.connect(self.changing_algorithm)

        # slots for skim tab
        self.add_skim.clicked.connect(self.select_skim)

        self.changing_algorithm()



    def select_skim(self):
        pass

    def load_graph(self):
        self.lbl_graphfile.setText('')
        file_types = "AequilibraE graph(*.aeg)"
        graph_file = QFileDialog.getOpenFileName(None, 'Traffic Assignment', self.path, file_types)
        if len(graph_file) > 0:
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
        else:
            self.graph = Graph()

    def browse_outfile(self):
        file_types = "Comma-separated files(*.csv);;Numpy Binnary Array(*.npy)"
        new_name = QFileDialog.getSaveFileName(None, 'Result matrix', self.path, file_types)
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
                lids = self.graph.graph['link_id']
                direcs = self.graph.graph['direction']

                dt = [('Link ID', np.int), ('AB Flow', np.float), ('BA Flow', np.float), ('Tot Flow', np.float)]
                res = np.zeros(np.max(lids) +1, dtype = dt)

                res['Link ID'][:] = np.arange(np.max(lids) + 1)[:]

                # Indices of links BA and AB
                ABs = direcs < 0
                BAs = direcs > 0

                link_flows = self.results.results()[:-1]

                # AB Flows
                link_ids = lids[ABs]
                res['AB Flow'][link_ids] = link_flows[ABs]

                # BA Flows
                link_ids = lids[BAs]
                res['BA Flow'][link_ids] = link_flows[BAs]

                # Tot Flow
                res['Tot Flow'] = res['AB Flow'] + res['BA Flow']
                np.savetxt(self.outname, res, delimiter = ',', header='Link_ID,AB Flow,BA Flow,Tot Flow')
                # outp = open(self.outname, 'w')
                # print >> outp, 'Link_ID,AB Flow,BA Flow,Tot Flow'
                # for k in res:
                #     print >> outp, str(k[0]) + ',' + str(k[1]) + ',' + str(k[2]) + ',' + str(k[3])
                # outp.flush()
                # outp.close()
        self.exit_procedure()

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

        if not len(self.network_layer.currentText()):
            self.error = 'No line layer selected'

        if not len(self.network_field.currentText()):
            self.error = 'No link ID field selected'

        if self.outname is None:
            self.error = 'Parameters for output missing'

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


    def exit_procedure(self):
        self.close()
        if len(self.report) > 0:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()




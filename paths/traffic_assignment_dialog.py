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
from load_select_link_query_builder import LoadSelectLinkQueryBuilder


class TrafficAssignmentDialog(QDialog, Ui_traffic_assignment):
    def __init__(self, iface):
        class OutputType:
            def __init__(self):
                self.temp_file = None
                self.extension = None
                self.output_name = None

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

        # path file
        self.do_path_file.stateChanged.connect(self.change_status_for_path_file)
        self.select_path_file_name.clicked.connect(self.choose_output_for_path_file)
        self.do_path_file.setEnabled(False)
        self.path_file = OutputType
        self.change_status_for_path_file()

        # Queries
        tables = [self.select_link_list, self.list_link_extraction]
        for table in tables:
            table.setColumnWidth(0, 280)
            table.setColumnWidth(1, 40)
            table.setColumnWidth(2, 150)
            table.setColumnWidth(3, 40)

        #critical link
        self.but_build_query.clicked.connect(partial(self.build_query, 'select link'))
        self.do_select_link.stateChanged.connect(self.set_behavior_special_analysis)
        self.tot_crit_link_queries = 0
        self.critical_output = OutputType

        # link flow extraction
        self.but_build_query_extract.clicked.connect(partial(self.build_query, 'Link flow extraction'))
        self.do_extract_link_flows.stateChanged.connect(self.set_behavior_special_analysis)
        self.tot_link_flow_extract = 0
        self.link_extract = OutputType

    def build_query(self, purpose):
        if purpose == 'select link':
            button = self.but_build_query
            message = 'Select Link Analysis'
            table = self.select_link_list
            counter = self.tot_crit_link_queries

        if purpose == 'Link flow extraction':
            button = self.but_build_query_extract
            message = 'Link flow extraction'
            table = self.list_link_extraction
            counter = self.tot_link_flow_extract

        button.setEnabled(False)
        dlg2 = LoadSelectLinkQueryBuilder(self.iface, self.graph.graph, message)
        dlg2.exec_()

        if dlg2.links is not None:
            table.setRowCount(counter + 1)
            text = ''
            for i in dlg2.links:
                text = text + ', (' + i[0].encode('utf-8') + ', "' + i[1].encode('utf-8') + '")'
            text = text[2:]
            table.setItem(counter, 0, QTableWidgetItem(text))
            table.setItem(counter, 1, QTableWidgetItem(dlg2.query_type))
            table.setItem(counter, 2, QTableWidgetItem(dlg2.query_name))
            del_button = QPushButton('X')
            del_button.clicked.connect(partial(self.click_button_inside_the_list, purpose))
            table.setCellWidget(counter, 3, del_button)
            counter += 1

        if purpose == 'select link':
            self.tot_crit_link_queries = counter

        elif purpose == 'Link flow extraction':
            self.tot_link_flow_extract = counter

        button.setEnabled(True)

    def click_button_inside_the_list(self, purpose):
        if purpose == 'select link':
            table = self.select_link_list
        elif purpose == 'Link flow extraction':
            table = self.list_link_extraction

        button = self.sender()
        index = self.select_link_list.indexAt(button.pos())
        row = index.row()
        table.removeRow(row)

        if purpose == 'select link':
            self.tot_crit_link_queries -= 1
        elif purpose == 'Link flow extraction':
            self.tot_link_flow_extract -= 1

    def choose_output_for_path_file(self):
        new_name, file_type = GetOutputFileName(self, 'Path File', ["AequilibraE Path File(*.aep)"], ".aep", self.path)

        if new_name is not None:
            self.path_file.extension = file_type
            self.path_file.output_name = new_name
            self.path_file_display.setText(new_name)
            self.path_file.temp_file = self.temp_path + uuid.uuid4().hex
            self.results.setSavePathFile(True, self.path_file.temp_file + '.aep')
        else:
            self.path_file.output_name = None
            self.path_file_display.setText('...')

    def choose_output_for_critical_link(self):
        new_name, type = GetOutputFileName(self, 'Select Link analysis', ["Select Link Analysis Matrix(*.aes)",
                                                 "NumPy Array(*.npy)", "SQLite(*.sqlite)"], ".aes", self.path)

        if new_name is not None:
            self.critical_link_output_file = new_name
            self.critical_matrix_path.setText(new_name)
            self.critical_link_temp_file = self.temp_path + uuid.uuid4().hex

            self.results.setCriticalLinks(True, self.critical_queries, self.critical_link_temp_file + '.aes')
        else:
            self.critical_link_output_file = None
            self.critical_matrix_path.setText('...')

    def change_status_for_path_file(self):
        if self.do_path_file.isChecked():
            self.select_path_file_name.setEnabled(True)
            self.path_file_display.setVisible(True)
        else:
            self.select_path_file_name.setEnabled(False)
            self.path_file_display.setVisible(False)
            self.path_file.output_name = None
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
        else:
            self.graph = Graph()
        self.change_status_for_path_file()
        self.set_behavior_special_analysis()

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

    def set_behavior_special_analysis(self):
        if self.graph.num_links < 1:
            behavior = False
        else:
            behavior = True

        self.do_path_file.setEnabled(behavior)

        # This line of code turns off the features of select link analysis and link flow extraction while these
        #features are still being developed
        behavior = False

        self.do_select_link.setEnabled(behavior)
        self.do_extract_link_flows.setEnabled(behavior)

        self.but_build_query.setEnabled(behavior * self.do_select_link.isChecked())
        self.select_link_list.setEnabled(behavior * self.do_select_link.isChecked())

        self.list_link_extraction.setEnabled(behavior * self.do_extract_link_flows.isChecked())
        self.but_build_query_extract.setEnabled(behavior * self.do_extract_link_flows.isChecked())

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

        if self.do_path_file.isChecked() and self.path_file.output_name is None:
            self.error = 'No output file name for the path file selected'

        if self.error is not None:
            return False
        else:
            return True

    def load_assignment_queries(self):
        # First we load the assignment queries
        query_labels=[]
        query_elements = []
        query_types=[]
        if self.tot_crit_link_queries:
            for i in range(self.tot_crit_link_queries):
                links = eval(self.select_link_list.item(i, 0).text())
                query_type = self.select_link_list.item(i, 1).text()
                query_name = self.select_link_list.item(i, 2).text()

                for l in links:
                    d = directions_dictionary[l[1]]
                    lk = self.graph.ids[(self.graph.graph['link_id'] == int(l[0])) & (self.graph.graph['direction'] == d)]

                query_labels.append(query_name)
                query_elements.append(lk)
                query_types(query_type)

        self.critical_queries = {'labels': query_labels,
                                 'elements': query_elements,
                                 ' type': query_types}

    def progress_range_from_thread(self, val):
        self.progressbar0.setRange(0, val)

    def progress_value_from_thread(self, val):
        self.progressbar0.setValue(val)

    def progress_text_from_thread(self, val):
        self.progress_label0.setText(val)

    def produce_all_outputs(self):

        # Save link flows to disk
        self.results.save_loads_to_disk(self.outname)

        # Path file
        if self.do_path_file.isChecked():
            if self.method['algorithm'] == 'AoN':
                del(self.results.path_file['results'])
                self.results.path_file = None

                shutil.move(self.path_file.temp_file + '.aep', self.path_file.output_name)
                shutil.move(self.path_file.temp_file + '.aed', self.path_file.output_name[:-3] + 'aed')

        # select link analysis
        if self.do_path_file.isChecked():
            if self.method['algorithm'] == 'AoN':
                del(self.results.critical_links['results'])
                self.results.critical_links = None

                shutil.move(self.critical_output.temp_file + '.aep', self.critical_output.output_name)
                shutil.move(self.critical_output.temp_file + '.aed', self.critical_output.output_name[:-3] + 'aed')

        if self.do_select_link.isChecked():
            if self.method['algorithm'] == 'AoN':
                del(self.results.critical_links['results'])
                self.results.critical_links = None

                shutil.move(self.critical_output.temp_file + '.aep', self.critical_output.output_name)
                shutil.move(self.critical_output.temp_file + '.aed', self.critical_output.output_name[:-3] + 'aed')

        if self.do_extract_link_flows.isChecked():
            if self.method['algorithm'] == 'AoN':
                del(self.results.link_extraction['results'])
                self.results.link_extraction = None

                shutil.move(self.link_extract.temp_file + '.aep', self.link_extract.output_name)
                shutil.move(self.link_extract.temp_file + '.aed', self.link_extract.output_name[:-3] + 'aed')

        self.exit_procedure()

    def exit_procedure(self):
        self.close()
        if len(self.report) > 0:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()


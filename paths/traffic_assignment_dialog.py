"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Traffic assignment
 Purpose:    Loads GUI to perform traffic assignment procedures

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:   Pedro Camargo
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-10-30
 Updated:... 2017-06-07
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, QtCore, uic
from qgis.gui import QgsMapLayerProxyModel, QgsFieldProxyModel
import sys
import os
from functools import partial
import numpy as np
import uuid
import shutil

from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import *
from ..common_tools import LoadMatrixDialog
from ..common_tools import ReportDialog
from ..common_tools import NumpyModel
from ..common_tools import GetOutputFolderName, GetOutputFileName

from traffic_assignment_procedure import TrafficAssignmentProcedure
from load_select_link_query_builder_dialog import LoadSelectLinkQueryBuilderDialog

no_binary = False
try:
    from aequilibrae.paths import Graph, AssignmentResults
except:
    no_binary = True

sys.modules['qgsmaplayercombobox'] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_traffic_assignment.ui'))


class TrafficAssignmentDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.output_path = None
        self.temp_path = None
        self.error = None
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

        # Signals for the algorithm tab
        self.progressbar0.setVisible(False)
        self.progressbar0.setValue(0)
        self.progress_label0.setVisible(False)

        self.do_assignment.clicked.connect(self.run)
        self.cancel_all.clicked.connect(self.exit_procedure)
        self.select_output_folder.clicked.connect(self.choose_folder_for_outputs)

        self.cb_choose_algorithm.addItem('All-Or-Nothing')
        self.cb_choose_algorithm.currentIndexChanged.connect(self.changing_algorithm)

        # slots for skim tab
        self.add_skim.clicked.connect(self.select_skim)

        self.changing_algorithm()

        # path file
        self.path_file = OutputType()

        # Queries
        tables = [self.select_link_list, self.list_link_extraction]
        for table in tables:
            table.setColumnWidth(0, 280)
            table.setColumnWidth(1, 40)
            table.setColumnWidth(2, 150)
            table.setColumnWidth(3, 40)

        self.graph_properties_table.setColumnWidth(0,190)
        self.graph_properties_table.setColumnWidth(1,240)
        #critical link
        self.but_build_query.clicked.connect(partial(self.build_query, 'select link'))
        self.do_select_link.stateChanged.connect(self.set_behavior_special_analysis)
        self.tot_crit_link_queries = 0
        self.critical_output = OutputType()

        # link flow extraction
        self.but_build_query_extract.clicked.connect(partial(self.build_query, 'Link flow extraction'))
        self.do_extract_link_flows.stateChanged.connect(self.set_behavior_special_analysis)
        self.tot_link_flow_extract = 0
        self.link_extract = OutputType()

        # Disabling resources not yet implemented
        self.do_output_to_csv.setEnabled(False)
        self.do_select_link.setEnabled(False)
        self.but_build_query.setEnabled(False)
        self.select_link_list.setEnabled(False)

        self.do_extract_link_flows.setEnabled(False)
        self.but_build_query_extract.setEnabled(False)
        self.list_link_extraction.setEnabled(False)


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
        dlg2 = LoadSelectLinkQueryBuilderDialog(self.iface, self.graph.graph, message)
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

    def choose_folder_for_outputs(self):
        new_name = GetOutputFolderName(self.path, 'Output folder for traffic assignment')
        if new_name:
            self.output_path = new_name
            self.lbl_output.setText(new_name)
        else:
            self.output_path = None
            self.lbl_output.setText(new_name)

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
            not_considering_list.append('direction')

            for i in list(self.graph.graph.dtype.names):
                if i not in not_considering_list:
                    self.minimizing_field.addItem(i)
            self.lbl_graphfile.setText(graph_file)

            self.results.prepare(self.graph)
            cores = get_parameter_chain(['system', 'cpus'])
            self.results.set_cores(cores)

            # show graph properties
            def centers_item(item):
                cell_widget = QWidget()
                lay_out = QHBoxLayout(cell_widget)
                lay_out.addWidget(item)
                lay_out.setAlignment(Qt.AlignCenter)
                lay_out.setContentsMargins(0, 0, 0, 0)
                cell_widget.setLayout(lay_out)
                return cell_widget

            self.graph_properties_table.clearContents()
            self.graph_properties_table.setRowCount(5)

            self.graph_properties_table.setItem(0, 0, QTableWidgetItem('Graph ID'))
            self.graph_properties_table.setItem(0, 1, QTableWidgetItem(self.graph.__id__))

            self.graph_properties_table.setItem(1, 0, QTableWidgetItem('Number of links'))
            self.graph_properties_table.setItem(1, 1, QTableWidgetItem(str(self.graph.num_links)))

            self.graph_properties_table.setItem(2, 0, QTableWidgetItem('Number of nodes'))
            self.graph_properties_table.setItem(2, 1, QTableWidgetItem(str(self.graph.num_nodes)))

            self.graph_properties_table.setItem(3, 0, QTableWidgetItem('Number of centroids'))
            self.graph_properties_table.setItem(3, 1, QTableWidgetItem(str(self.graph.centroids)))

            self.graph_properties_table.setItem(4, 0, QTableWidgetItem('Block flows through centroids'))
            chb2 = QCheckBox()
            chb2.setChecked(self.graph.block_centroid_flows)
            self.graph_properties_table.setCellWidget(4, 1, centers_item(chb2))


        else:
            self.graph = Graph()
        self.set_behavior_special_analysis()

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


    def changing_algorithm(self):
        if self.cb_choose_algorithm.currentText() == 'All-Or-Nothing':
            self.method['algorithm'] = 'AoN'

    def run_thread(self):
        self.progress_label0.setVisible(True)
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
        if self.worker_thread.report:
            self.report = self.worker_thread.report
        else:
            self.output = self.results.link_loads
            self.report = self.worker_thread.report

            self.produce_all_outputs()
        self.exit_procedure()

    def run(self):
        if self.check_data():
            self.set_output_names()
            self.progressbar0.setVisible(True)
            self.worker_thread = TrafficAssignmentProcedure(qgis.utils.iface.mainWindow(), self.matrix, self.graph,
                                                       self.results, self.method)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input error", self.error, level=3)

    def set_output_names(self):
        self.path_file.temp_file = os.path.join(self.temp_path, 'path_file')
        self.path_file.output_name = os.path.join(self.output_path, 'path_file')
        self.path_file.extension = 'aed'

        if self.do_path_file.isChecked():
            self.results.setSavePathFile(save=True,path_result=self.path_file.temp_file)

        self.link_extract.temp_file = os.path.join(self.temp_path, 'link_extract')
        self.link_extract.output_name = os.path.join(self.output_path, 'link_extract')
        self.link_extract.extension = 'aed'

        self.critical_output.temp_file = os.path.join(self.temp_path, 'critical_output')
        self.critical_output.output_name = os.path.join(self.output_path, 'critical_output')
        self.critical_output.extension = 'aed'

    def check_data(self):
        self.error = None

        if self.matrix is None:
            self.error = 'Demand matrix missing'

        if not self.graph.num_links:
            self.error = 'Graph was not loaded'

        if self.output_path is None:
            self.error = 'Parameters for output missing'

        if self.results.zones != np.max(self.matrix.shape[:]):
            self.error = 'Number of zones in the graph ({0}) does not match the number of ' \
                         'zones in your matrix ({1})'.format(self.results.zones, np.max(self.matrix.shape[:]))

        if self.error is not None:
            return False

        else:
            self.temp_path = os.path.join(self.output_path, 'temp')
            if not os.path.exists(self.temp_path):
                os.makedirs(self.temp_path)
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
        if self.do_output_to_sqlite.isChecked():
            self.results.save_to_disk(output='loads',
                                      output_file_name = os.path.join(self.output_path, 'link_flows.db'),
                                      file_type='sqlite')
        else:
            self.results.save_to_disk(output='loads',
                                      output_file_name = os.path.join(self.output_path, 'link_flows.csv'),
                                      file_type='csv')

        # save Path file if that is the case
        if self.do_path_file.isChecked():
            if self.method['algorithm'] == 'AoN':
                if self.do_output_to_sqlite.isChecked():
                    self.results.save_to_disk(output='path_file',
                                              output_file_name = os.path.join(self.output_path, 'path_file.db'),
                                              file_type='sqlite')
                else:
                    shutil.move(self.path_file.temp_file + '.aep', self.path_file.output_name + '.aep')
                    shutil.move(self.path_file.temp_file + '.aed', self.path_file.output_name + '.aed')


        # if self.do_select_link.isChecked():
        #     if self.method['algorithm'] == 'AoN':
        #         del(self.results.critical_links['results'])
        #         self.results.critical_links = None
        #
        #         shutil.move(self.critical_output.temp_file + '.aep', self.critical_output.output_name)
        #         shutil.move(self.critical_output.temp_file + '.aed', self.critical_output.output_name[:-3] + 'aed')
        #
        # if self.do_extract_link_flows.isChecked():
        #     if self.method['algorithm'] == 'AoN':
        #         del(self.results.link_extraction['results'])
        #         self.results.link_extraction = None
        #
        #         shutil.move(self.link_extract.temp_file + '.aep', self.link_extract.output_name)
        #         shutil.move(self.link_extract.temp_file + '.aed', self.link_extract.output_name[:-3] + 'aed')

        self.exit_procedure()

    def exit_procedure(self):
        self.close()
        if self.report:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()


class OutputType():
    def __init__(self):
        self.temp_file = None
        self.extension = None
        self.output_name = None
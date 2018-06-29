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
 Updated:... 2017-12-11
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, uic
from qgis.gui import QgsMapLayerProxyModel
import sys
from functools import partial
import numpy as np
from collections import OrderedDict

from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import *
from ..matrix_procedures import LoadMatrixDialog
from ..common_tools import ReportDialog
from ..common_tools import GetOutputFolderName, GetOutputFileName
from ..aequilibrae.aequilibrae.matrix import AequilibraeMatrix

from load_select_link_query_builder_dialog import LoadSelectLinkQueryBuilderDialog

no_binary = False
try:
    from ..aequilibrae.aequilibrae.paths import Graph, AssignmentResults, allOrNothing
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
        self.report = None
        self.method = {}
        self.matrices = OrderedDict()
        self.skims = []
        self.matrix = None
        self.graph = Graph()
        self.results = AssignmentResults()
        self.block_centroid_flows = None
        self.worker_thread = None

        # Signals for the matrix_procedures tab
        self.but_load_new_matrix.clicked.connect(self.find_matrices)

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
        self.but_build_query.clicked.connect(partial(self.build_query, 'select link'))

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

        self.graph_properties_table.setColumnWidth(0, 190)
        self.graph_properties_table.setColumnWidth(1, 240)

        # critical link
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
        self.do_select_link.setEnabled(False)
        self.but_build_query.setEnabled(False)
        self.select_link_list.setEnabled(False)

        self.do_extract_link_flows.setEnabled(False)
        self.but_build_query_extract.setEnabled(False)
        self.list_link_extraction.setEnabled(False)
        self.new_matrix_to_assign()

        self.table_matrix_list.setColumnWidth(0, 135)
        self.table_matrix_list.setColumnWidth(1, 135)
        self.table_matrices_to_assign.setColumnWidth(0, 125)
        self.table_matrices_to_assign.setColumnWidth(1, 125)
        self.skim_list_table.setColumnWidth(0, 70)
        self.skim_list_table.setColumnWidth(1, 490)

    def choose_folder_for_outputs(self):
        new_name = GetOutputFolderName(self.path, 'Output folder for traffic assignment')
        if new_name:
            self.output_path = new_name
            self.lbl_output.setText(new_name)
        else:
            self.output_path = None
            self.lbl_output.setText(new_name)

    def load_graph(self):
        self.lbl_graphfile.setText('')

        file_types = ["AequilibraE graph(*.aeg)"]
        default_type = '.aeg'
        box_name = 'Traffic Assignment'
        graph_file, _ = GetOutputFileName(self, box_name, file_types, default_type, self.path)

        if graph_file is not None:
            self.graph.load_from_disk(graph_file)

            fields = list(set(self.graph.graph.dtype.names) - set(self.graph.required_default_fields))
            self.minimizing_field.addItems(fields)
            self.update_skim_list(fields)
            self.lbl_graphfile.setText(graph_file)

            cores = get_parameter_chain(['system', 'cpus'])
            self.results.set_cores(cores)

            # show graph properties
            def centers_item(qt_item):
                cell_widget = QWidget()
                lay_out = QHBoxLayout(cell_widget)
                lay_out.addWidget(qt_item)
                lay_out.setAlignment(Qt.AlignCenter)
                lay_out.setContentsMargins(0, 0, 0, 0)
                cell_widget.setLayout(lay_out)
                return cell_widget

            items = [['Graph ID', self.graph.__id__],
                     ['Number of links', self.graph.num_links],
                     ['Number of nodes', self.graph.num_nodes],
                     ['Number of centroids', self.graph.num_zones]]

            self.graph_properties_table.clearContents()
            self.graph_properties_table.setRowCount(5)
            for i, item in enumerate(items):
                self.graph_properties_table.setItem(i, 0, QTableWidgetItem(item[0]))
                self.graph_properties_table.setItem(i, 1, QTableWidgetItem(str(item[1])))

            self.graph_properties_table.setItem(4, 0, QTableWidgetItem('Block flows through centroids'))
            self.block_centroid_flows = QCheckBox()
            self.block_centroid_flows.setChecked(self.graph.block_centroid_flows)
            self.graph_properties_table.setCellWidget(4, 1, centers_item(self.block_centroid_flows))
        else:
            self.graph = Graph()
        self.set_behavior_special_analysis()

    def changing_algorithm(self):
        if self.cb_choose_algorithm.currentText() == 'All-Or-Nothing':
            self.method['algorithm'] = 'AoN'

    def run_thread(self):

        QObject.connect(self.worker_thread, SIGNAL("assignment"), self.signal_handler)
        self.worker_thread.start()
        self.exec_()

    def job_finished_from_thread(self):
        self.report = self.worker_thread.report
        self.produce_all_outputs()

        self.exit_procedure()

    def run(self):
        if self.check_data():
            self.set_output_names()
            self.progress_label0.setVisible(True)
            self.progressbar0.setVisible(True)
            self.progressbar0.setRange(0, self.graph.num_zones)
            try:
                if self.method['algorithm'] == 'AoN':
                    self.worker_thread = allOrNothing(self.matrix, self.graph, self.results)
                self.run_thread()
            except ValueError as error:
                qgis.utils.iface.messageBar().pushMessage("Input error", error.message, level=3)
        else:
            qgis.utils.iface.messageBar().pushMessage("Input error", self.error, level=3)

    def set_output_names(self):
        self.path_file.temp_file = os.path.join(self.temp_path, 'path_file.aed')
        self.path_file.output_name = os.path.join(self.output_path, 'path_file')
        self.path_file.extension = 'aed'

        if self.do_path_file.isChecked():
            self.results.setSavePathFile(save=True, path_result=self.path_file.temp_file)

        self.link_extract.temp_file = os.path.join(self.temp_path, 'link_extract')
        self.link_extract.output_name = os.path.join(self.output_path, 'link_extract')
        self.link_extract.extension = 'aed'

        self.critical_output.temp_file = os.path.join(self.temp_path, 'critical_output')
        self.critical_output.output_name = os.path.join(self.output_path, 'critical_output')
        self.critical_output.extension = 'aed'

    def check_data(self):
        self.error = None

        self.change_graph_settings()

        if not self.graph.num_links:
            self.error = 'Graph was not loaded'
            return False

        self.matrix = None
        self.prepare_assignable_matrices()
        if self.matrix is None:
            self.error = 'Demand matrix missing'
            return False

        if self.output_path is None:
            self.error = 'Parameters for output missing'
            return False

        self.temp_path = os.path.join(self.output_path, 'temp')
        if not os.path.exists(self.temp_path):
            os.makedirs(self.temp_path)

        self.results.prepare(self.graph, self.matrix)
        return True

    def load_assignment_queries(self):
        # First we load the assignment queries
        query_labels = []
        query_elements = []
        query_types = []
        if self.tot_crit_link_queries:
            for i in range(self.tot_crit_link_queries):
                links = eval(self.select_link_list.item(i, 0).text())
                query_type = self.select_link_list.item(i, 1).text()
                query_name = self.select_link_list.item(i, 2).text()

                for l in links:
                    d = directions_dictionary[l[1]]
                    lk = self.graph.ids[(self.graph.graph['link_id'] == int(l[0])) &
                                        (self.graph.graph['direction'] == d)]

                query_labels.append(query_name)
                query_elements.append(lk)
                query_types.append(query_type)

        self.critical_queries = {'labels': query_labels,
                                 'elements': query_elements,
                                 ' type': query_types}

    def signal_handler(self, val):
        if val[0] == 'zones finalized':
            self.progressbar0.setValue(val[1])
        elif val[0] == 'text AoN':
            self.progress_label0.setText(val[1])
        elif val[0] == 'finished_threaded_procedure':
            self.job_finished_from_thread()

    # TODO: Write code to export skims
    def produce_all_outputs(self):

        extension = 'aed'
        if not self.do_output_to_aequilibrae.isChecked():
            extension = 'csv'
            if self.do_output_to_sqlite.isChecked():
                extension = 'sqlite'

        # Save link flows to disk
        self.results.save_to_disk(os.path.join(self.output_path, 'link_flows.' + extension), output='loads')

        # save Path file if that is the case
        if self.do_path_file.isChecked():
            if self.method['algorithm'] == 'AoN':
                if self.do_output_to_sqlite.isChecked():
                    self.results.save_to_disk(file_name=os.path.join(self.output_path, 'path_file.' + extension),
                                              output='path_file')

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


# Procedures related to critical analysis. Not yet fully implemented
    def build_query(self, purpose):
        if purpose == 'select link':
            button = self.but_build_query
            message = 'Select Link Analysis'
            table = self.select_link_list
            counter = self.tot_crit_link_queries
        else:
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
        else:
            table = self.list_link_extraction

        button = self.sender()
        index = self.select_link_list.indexAt(button.pos())
        row = index.row()
        table.removeRow(row)

        if purpose == 'select link':
            self.tot_crit_link_queries -= 1
        elif purpose == 'Link flow extraction':
            self.tot_link_flow_extract -= 1

    def set_behavior_special_analysis(self):
        if self.graph.num_links < 1:
            behavior = False
        else:
            behavior = True

        self.do_path_file.setEnabled(behavior)

        # This line of code turns off the features of select link analysis and link flow extraction while these
        # features are still being developed
        behavior = False

        self.do_select_link.setEnabled(behavior)
        self.do_extract_link_flows.setEnabled(behavior)

        self.but_build_query.setEnabled(behavior * self.do_select_link.isChecked())
        self.select_link_list.setEnabled(behavior * self.do_select_link.isChecked())

        self.list_link_extraction.setEnabled(behavior * self.do_extract_link_flows.isChecked())
        self.but_build_query_extract.setEnabled(behavior * self.do_extract_link_flows.isChecked())

    def update_skim_list(self, skims):
        self.skim_list_table.clearContents()
        self.skim_list_table.setRowCount(len(skims))

        for i, skm in enumerate(skims):
            self.skim_list_table.setItem(i, 1, QTableWidgetItem(skm))
            chb = QCheckBox()
            my_widget = QWidget()
            lay_out = QHBoxLayout(my_widget)
            lay_out.addWidget(chb)
            lay_out.setAlignment(Qt.AlignCenter)
            lay_out.setContentsMargins(0, 0, 0, 0)
            my_widget.setLayout(lay_out)

            self.skim_list_table.setCellWidget(i, 0, my_widget)

    # All Matrix loading and assignables selection
    def update_matrix_list(self):
        self.table_matrix_list.clearContents()
        self.table_matrix_list.clearContents()
        self.table_matrix_list.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.table_matrix_list.setRowCount(len(self.matrices.keys()))

        for i, data_name in enumerate(self.matrices.keys()):
            self.table_matrix_list.setItem(i, 0, QTableWidgetItem(data_name))

            cbox = QComboBox()
            for idx in self.matrices[data_name].index_names:
                cbox.addItem(str(idx))
            self.table_matrix_list.setCellWidget(i, 1, cbox)

    def find_matrices(self):
        dlg2 = LoadMatrixDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.matrix is not None:
            matrix_name = dlg2.matrix.file_path
            matrix_name = os.path.splitext(os.path.basename(matrix_name))[0]
            matrix_name = self.find_non_conflicting_name(matrix_name, self.matrices)
            self.matrices[matrix_name] = dlg2.matrix
            self.update_matrix_list()

            row_count = self.table_matrices_to_assign.rowCount()
            new_matrix = list(self.matrices.keys())[-1]

            for i in range(row_count):
                cb = self.table_matrices_to_assign.cellWidget(i, 0)
                cb.insertItem(-1, new_matrix)

    def find_non_conflicting_name(self, data_name, dictio):
        if data_name in dictio:
            i = 1
            new_data_name = data_name + '_' + str(i)
            while new_data_name in dictio:
                i += 1
                new_data_name = data_name + '_' + str(i)
            data_name = new_data_name
        return data_name

    def changed_assignable_matrix(self, mi):
        chb = self.sender()
        mat_name = chb.currentText()

        table = self.table_matrices_to_assign
        for row in range(table.rowCount()):
            if table.cellWidget(row, 0) == chb:
                break

        if len(mat_name) == 0:
            if row + 1 < table.rowCount():
                self.table_matrices_to_assign.removeRow(row)
        else:
            mat_cores = self.matrices[mat_name].names
            cbox2 = QComboBox()
            cbox2.addItems(mat_cores)
            self.table_matrices_to_assign.setCellWidget(row, 1, cbox2)

            if row + 1 == table.rowCount():
                self.new_matrix_to_assign()

    def new_matrix_to_assign(self):
        # We edit ALL the combo boxes to have the current list of matrices
        row_count = self.table_matrices_to_assign.rowCount()
        self.table_matrices_to_assign.setRowCount(row_count + 1)

        cbox = QComboBox()
        cbox.addItems(list(self.matrices.keys()))
        cbox.addItem('')
        cbox.setCurrentIndex(cbox.count()-1)
        cbox.currentIndexChanged.connect(self.changed_assignable_matrix)
        self.table_matrices_to_assign.setCellWidget(row_count, 0, cbox)


    def prepare_assignable_matrices(self):
        table = self.table_matrices_to_assign
        idx = self.graph.centroids
        mat_names = []
        if table.rowCount() > 1:
            for row in range(table.rowCount() - 1):
                mat = table.cellWidget(row, 0).currentText()
                core = table.cellWidget(row, 1).currentText()

                if not np.array_equal(idx,self.matrices[mat].index):
                    self.error = 'Assignable matrix ' + mat + ' has indices that do not match the centroids'
                if core in mat_names:
                    self.error = 'Assignable matrices cannot have same names'
                mat_names.append(core.encode('utf-8'))

            self.matrix = AequilibraeMatrix()
            self.matrix.create_empty(file_name=self.matrix.random_name(),
                                         zones=idx.shape[0],
                                         matrix_names=mat_names)
            self.matrix.index[:] = idx[:]

            for row in range(table.rowCount() - 1):
                mat = table.cellWidget(row, 0).currentText()
                core = table.cellWidget(row, 1).currentText()
                self.matrix.matrix[core][:, :] = self.matrices[mat].matrix[core][:, :]
            self.matrix.computational_view()
        else:
            self.error = 'You need to have at least one matrix to assign'

        # Run preparation procedures
    def change_graph_settings(self):
        skims = []
        table = self.skim_list_table
        for i in range(table.rowCount()):
            for chb in table.cellWidget(i, 0).findChildren(QCheckBox):
                if chb.isChecked():
                    skims.append(table.item(i, 1).text().encode('utf-8'))

        if len(skims) == 0:
            skims = False

        self.graph.set_graph(cost_field=self.minimizing_field.currentText(),
                             skim_fields=skims,
                             block_centroid_flows=self.block_centroid_flows.isChecked())

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
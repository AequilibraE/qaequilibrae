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
 Updated:... 2018-12-27
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt import QtWidgets, uic, QtCore, QtGui
from qgis.PyQt.QtGui import *

import sys
from functools import partial
import numpy as np
from collections import OrderedDict
import importlib.util as iutil
from ..common_tools.global_parameters import *
from ..common_tools.auxiliary_functions import *
from ..matrix_procedures import LoadMatrixDialog
from ..common_tools import ReportDialog, only_str
from ..common_tools import GetOutputFolderName, GetOutputFileName
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths.traffic_assignment import TrafficAssignment
from aequilibrae.paths.traffic_class import TrafficClass
from aequilibrae.paths.vdf import VDF, all_vdf_functions
from .load_select_link_query_builder_dialog import LoadSelectLinkQueryBuilderDialog
from aequilibrae import Parameters

no_binary = False
try:
    from aequilibrae.paths import Graph, AssignmentResults, allOrNothing
    from aequilibrae.project import Project
except:
    no_binary = True

# Checks if we can display OMX
spec = iutil.find_spec("openmatrix")
has_omx = spec is not None
if has_omx:
    import openmatrix as omx

sys.modules["qgsmaplayercombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_traffic_assignment.ui"))


class TrafficAssignmentDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, project: Project):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.project = project
        self.setupUi(self)
        self.path = standard_path()
        self.output_path = None
        self.temp_path = None
        self.error = None
        self.report = None
        self.current_modes = []
        self.assignment = TrafficAssignment()
        self.traffic_classes = {}
        self.vdf_parameters = {}
        self.skims = {}
        self.matrix = None
        self.block_centroid_flows = None
        self.worker_thread = None
        self.all_modes = {}
        self.__populate_project_info()

        # Signals for the matrix_procedures tab
        self.but_load_new_matrix.clicked.connect(self.find_matrices)
        self.but_add_skim.clicked.connect(self.__add_skimming)
        self.but_add_class.clicked.connect(self.__create_traffic_class)

        # Signals for the algorithm tab
        for q in [self.progressbar0, self.progressbar1, self.progress_label0, self.progress_label1]:
            q.setVisible(False)

        self.do_assignment.clicked.connect(self.run)
        self.cancel_all.clicked.connect(self.exit_procedure)
        self.select_output_folder.clicked.connect(self.choose_folder_for_outputs)

        for algo in self.assignment.all_algorithms:
            self.cb_choose_algorithm.addItem(algo)
        self.cb_choose_algorithm.setCurrentIndex(len(self.assignment.all_algorithms) - 1)

        for vdf in all_vdf_functions:
            self.cob_vdf.addItem(vdf)

        self.cob_vdf.currentIndexChanged.connect(self.__change_vdf)

        parameters = Parameters().parameters["assignment"]["equilibrium"]
        self.rel_gap.setText(str(parameters["rgap"]))
        self.max_iter.setText(str(parameters["maximum_iterations"]))

        # path file
        self.path_file = OutputType()

        # Queries
        tables = [self.select_link_list, self.list_link_extraction]
        for table in tables:
            table.setColumnWidth(0, 280)
            table.setColumnWidth(1, 40)
            table.setColumnWidth(2, 150)
            table.setColumnWidth(3, 40)

        self.tbl_project_properties.setColumnWidth(0, 120)
        self.tbl_project_properties.setColumnWidth(1, 450)

        # critical link
        # self.but_build_query.clicked.connect(partial(self.build_query, "select link"))
        # self.do_select_link.stateChanged.connect(self.set_behavior_special_analysis)
        # self.tot_crit_link_queries = 0
        # self.critical_output = OutputType()

        # link flow extraction
        # self.but_build_query_extract.clicked.connect(partial(self.build_query, "Link flow extraction"))
        # self.do_extract_link_flows.stateChanged.connect(self.set_behavior_special_analysis)
        # self.tot_link_flow_extract = 0
        # self.link_extract = OutputType()

        # Disabling resources not yet implemented
        self.do_select_link.setEnabled(False)
        self.but_build_query.setEnabled(False)
        self.select_link_list.setEnabled(False)
        self.do_extract_link_flows.setEnabled(False)
        self.but_build_query_extract.setEnabled(False)
        self.list_link_extraction.setEnabled(False)

        self.table_matrix_list.setColumnWidth(0, 135)
        self.table_matrix_list.setColumnWidth(1, 135)
        self.tbl_traffic_classes.setColumnWidth(0, 125)
        self.tbl_traffic_classes.setColumnWidth(1, 125)
        self.skim_list_table.setColumnWidth(0, 200)
        self.skim_list_table.setColumnWidth(1, 200)
        self.skim_list_table.setColumnWidth(2, 200)
        self.skim_list_table.setColumnWidth(3, 200)

        self.tbl_vdf_parameters.setColumnWidth(0, 75)
        self.tbl_vdf_parameters.setColumnWidth(1, 75)
        self.tbl_vdf_parameters.setColumnWidth(2, 140)

        self.__change_vdf()

    def __populate_project_info(self):
        table = self.tbl_project_properties
        table.setRowCount(2)

        # i.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        table.setItem(0, 0, QTableWidgetItem('Project path'))
        table.setItem(0, 1, QTableWidgetItem(self.project.path_to_file))

        curr = self.project.network.conn.cursor()
        curr.execute("""select mode_name, mode_id from modes""")

        modes = []
        for x in curr.fetchall():
            modes.append(f'{x[0]} ({x[1]})')
            self.all_modes[f'{x[0]} ({x[1]})'] = x[1]
            self.skims[f'{x[0]} ({x[1]})'] = []
            self.traffic_classes[f'{x[0]} ({x[1]})'] = None

        table.setItem(1, 0, QTableWidgetItem('Modes'))
        table.setItem(1, 1, QTableWidgetItem(', '.join(modes)))

        self.cob_mode_for_class.clear()
        for m in modes:
            self.cob_mode_for_class.addItem(m)

        self.project.network.build_graphs()

        for cob in [self.cob_skims_available, self.cob_capacity, self.cob_ffttime]:
            cob.clear()
            for x in self.project.network.skimmable_fields():
                cob.addItem(x)

    def find_matrices(self):
        dlg2 = LoadMatrixDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.matrix is not None:
            matrix_name = dlg2.matrix.file_path
            matrix_name = os.path.splitext(os.path.basename(matrix_name))[0]
            self.matrix = dlg2.matrix  # type: AequilibraeMatrix
            table = self.table_matrix_list

            table.clearContents()
            table.setRowCount(len(self.matrix.names))

            for i, core in enumerate(self.matrix.names):
                core_item = QTableWidgetItem(core)
                core_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(i, 0, core_item)
                chb = QCheckBox()
                chb.setChecked(True)
                table.setCellWidget(i, 1, chb)

            self.cob_matrix_indices.clear()
            for idx_nm in dlg2.matrix.index_names:
                self.cob_matrix_indices.addItem(idx_nm)

    def __edit_skimming_modes(self):
        self.cob_skim_mode.clear()
        for mode in self.current_modes:
            self.cob_skim_mode.addItem(mode)

    def __change_vdf(self):
        table = self.tbl_vdf_parameters
        table.clearContents()
        if self.cob_vdf.currentText().lower() == 'bpr':
            parameters = ['alpha', 'beta']
        else:
            return

        self.tbl_vdf_parameters.setRowCount(len(parameters))
        for i, par in enumerate(parameters):
            core_item = QTableWidgetItem(par)
            core_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(i, 0, core_item)

            val_item = QLineEdit()
            table.setCellWidget(i, 1, val_item)

            val_fld = QComboBox()
            for x in self.project.network.skimmable_fields():
                val_fld.addItem(x)
            table.setCellWidget(i, 2, val_fld)

    def __create_traffic_class(self):
        table = self.table_matrix_list
        user_classes = []
        for i in range(table.rowCount()):
            if table.cellWidget(i, 1).isChecked():
                user_classes.append(only_str(table.item(i, 0).text()))
        if len(user_classes) == 0:
            return

        self.matrix.computational_view(user_classes)

        self.matrix.set_index(self.cob_matrix_indices.currentText())

        mode = self.cob_mode_for_class.currentText()
        graph = self.project.network.graphs[self.all_modes[mode]]
        pce = self.pce_setter.value()
        assigclass = TrafficClass(graph, self.matrix)
        assigclass.set_pce(pce)
        self.traffic_classes[mode] = assigclass

        num_classes = len([x for x in self.traffic_classes.values() if x is not None])

        table = self.tbl_traffic_classes
        table.setRowCount(num_classes)

        idx = num_classes - 1
        mode_item = QTableWidgetItem(mode)
        mode_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        table.setItem(idx, 0, mode_item)

        classes_item = QTableWidgetItem(str(len(user_classes)))
        classes_item.setTextAlignment(Qt.AlignHCenter)
        classes_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        table.setItem(idx, 1, classes_item)

        pce_item = QTableWidgetItem(str(round(pce, 4)))
        pce_item.setTextAlignment(Qt.AlignHCenter)
        pce_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        table.setItem(idx, 2, pce_item)

        but = QPushButton()
        but.setText('Remove')
        but.clicked.connect(self.__remove_class)
        but.setEnabled(False)
        table.setCellWidget(idx, 3, but)

        idx = self.cob_mode_for_class.currentIndex()
        self.cob_mode_for_class.removeItem(idx)
        self.current_modes.append(mode)
        self.__edit_skimming_modes()

    def __add_skimming(self):

        field = self.cob_skims_available.currentText()
        mode = self.cob_skim_mode.currentText()
        if field in self.skims[mode]:
            return

        table = self.skim_list_table
        idx = table.rowCount()
        table.setRowCount(idx + 1)

        mode_item = QTableWidgetItem(mode)
        mode_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        table.setItem(idx, 0, mode_item)

        classes_item = QTableWidgetItem(field)
        classes_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        table.setItem(idx, 1, classes_item)

        last_chb = QCheckBox()
        last_chb.setChecked(True)
        table.setCellWidget(idx, 2, last_chb)

        blended_chb = QCheckBox()
        blended_chb.setChecked(True)
        table.setCellWidget(idx, 3, blended_chb)

        self.skims[mode].append(field)

    def __remove_class(self):
        self.__edit_skimming_modes()

    def choose_folder_for_outputs(self):
        new_name = GetOutputFolderName(self.path, "Output folder for traffic assignment")
        if new_name:
            self.output_path = new_name
            self.lbl_output.setText(new_name)
        else:
            self.output_path = None
            self.lbl_output.setText(new_name)

    def run_thread(self):
        self.worker_thread.assignment.connect(self.signal_handler)
        if self.cb_choose_algorithm.currentText() != 'all-or-nothing':
            self.worker_thread.equilibration.connect(self.equilibration_signal_handler)
        self.worker_thread.start()
        self.exec_()

    def job_finished_from_thread(self):
        # self.report = self.worker_thread.report
        self.produce_all_outputs()

        self.exit_procedure()

    def run(self):
        if self.check_data():
            algorithm = self.cb_choose_algorithm.currentText()
            if algorithm != 'all-or-nothing':
                for q in [self.progressbar1, self.progress_label1]:
                    q.setVisible(True)
                self.progressbar1.setRange(0, int(self.max_iter.text()))

            for q in [self.progressbar0, self.progress_label0]:
                q.setVisible(True)
                self.progressbar0.setRange(0, self.project.network.count_centroids())

            # self.set_output_names()
            # try:
            if True:
                if algorithm == 'all-or-nothing':
                    cls = [x for x in self.traffic_classes.values() if x is not None][0]
                    self.worker_thread = allOrNothing(cls.matrix, cls.graph, cls.results)
                else:
                    self.assignment.set_classes([x for x in self.traffic_classes.values() if x is not None])
                    self.assignment.set_vdf(self.cob_vdf.currentText())
                    self.assignment.set_vdf_parameters(self.vdf_parameters)
                    self.assignment.set_capacity_field(self.cob_capacity.currentText())
                    self.assignment.set_time_field(self.cob_ffttime.currentText())
                    self.assignment.set_algorithm(self.cb_choose_algorithm.currentText())
                    self.assignment.max_iter = int(self.max_iter.text())
                    self.assignment.rgap_target = float(self.rel_gap.text())
                    self.worker_thread = self.assignment.assignment
                self.run_thread()

            # except ValueError as error:
            #     qgis.utils.iface.messageBar().pushMessage("Input error", error.message, level=3)
        else:
            qgis.utils.iface.messageBar().pushMessage("Input error", self.error, level=3)

    def check_data(self):
        # TODO: AoN needs to be single class
        self.error = None

        num_classes = len([x for x in self.traffic_classes.values() if x is not None])
        if not num_classes:
            self.error = "No traffic classes to assign"
            return False

        if self.output_path is None:
            self.error = "Parameters for output missing"
            return False

        self.temp_path = os.path.join(self.output_path, "temp")
        if not os.path.exists(self.temp_path):
            os.makedirs(self.temp_path)
        return self.change_graph_settings()

    def signal_handler(self, val):
        if val[0] == "zones finalized":
            self.progressbar0.setValue(val[1])
        elif val[0] == "text AoN":
            self.progress_label0.setText(val[1])
        elif val[0] == "finished_threaded_procedure":
            self.progressbar0.setValue(0)
            if self.cb_choose_algorithm.currentText() == 'all-or-nothing':
                self.job_finished_from_thread()

    def equilibration_signal_handler(self, val):
        if val[0] == "iterations":
            self.progressbar1.setValue(val[1])
        elif val[0] == "text":
            self.progress_label1.setText(val[1])
        elif val[0] == "finished_threaded_procedure":
            self.job_finished_from_thread()

    # Save link flows to disk
    def produce_all_outputs(self):
        fn = os.path.join(self.output_path, "skims.aem")

        if self.cb_choose_algorithm.currentText() == 'all-or-nothing':
            cls = [x for x in self.traffic_classes.values() if x is not None][0]
            cls.results.save_to_disk(os.path.join(self.output_path, f"link_flows_{cls.graph.mode}.csv"), output="loads")
            cls.results.save_to_disk(os.path.join(self.output_path, f"link_flows_{cls.graph.mode}.aed"), output="loads")
            if has_omx:
                cls.results.skims.export(os.path.join(self.output_path, "skims.omx"))
            else:
                cls.results.skims.export(fn)
            return

        table = self.skim_list_table
        skim_names = []
        for i in range(table.rowCount()):
            mode = self.all_modes[table.item(i, 0).text()]
            field = table.item(i, 1).text()
            last_iter = table.cellWidget(i, 2).isChecked()
            blended = table.cellWidget(i, 3).isChecked()
            if last_iter:
                skim_names.append(f'{field}_{mode}_final')
            if blended:
                skim_names.append(f'{field}_{mode}_blended')

        for cls in self.assignment.classes:
            cls.results.save_to_disk(os.path.join(self.output_path, f"link_flows_{cls.graph.mode}.csv"), output="loads")
            cls.results.save_to_disk(os.path.join(self.output_path, f"link_flows_{cls.graph.mode}.aed"), output="loads")

        # cls.results.skims.export(os.path.join(self.output_path, f'blended_skims_{cls.graph.mode}.aed'))
        if skim_names:
            args = {'file_name': fn,
                    'zones': self.project.network.count_centroids(),
                    'matrix_names': skim_names}
            skims = AequilibraeMatrix()
            skims.create_empty(**args)

            for i in range(table.rowCount()):
                mode_name = table.item(i, 0).text()
                mode = self.all_modes[mode_name]
                field = table.item(i, 1).text()
                last_iter = table.cellWidget(i, 2).isChecked()
                blended = table.cellWidget(i, 3).isChecked()

                cls = self.traffic_classes[mode_name]

                if last_iter:
                    mat_name = f'{field}_{mode}_final'
                    skims.matrix[mat_name][:, :] = cls._aon_results.skims.matrix[field][:, :]
                if blended:
                    mat_name = f'{field}_{mode}_blended'
                    skims.matrix[mat_name][:, :] = cls.results.skims.matrix[field][:, :]

            skims.index[:] = cls.matrix.index[:]
            if has_omx:
                skims.export(os.path.join(self.output_path, "skims.omx"))
                skims.close()
                del skims
                os.unlink(fn)

    def click_button_inside_the_list(self, purpose):
        if purpose == "select link":
            table = self.select_link_list
        else:
            table = self.list_link_extraction

        button = self.sender()
        index = self.select_link_list.indexAt(button.pos())
        row = index.row()
        table.removeRow(row)

        if purpose == "select link":
            self.tot_crit_link_queries -= 1
        elif purpose == "Link flow extraction":
            self.tot_link_flow_extract -= 1

    def update_matrix_list(self):
        # All Matrix loading and assignables selection
        self.table_matrix_list.clearContents()
        self.table_matrix_list.clearContents()
        self.table_matrix_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_matrix_list.setRowCount(len(self.matrices.keys()))

        for i, data_name in enumerate(self.matrices.keys()):
            self.table_matrix_list.setItem(i, 0, QTableWidgetItem(data_name))

            cbox = QComboBox()
            for idx in self.matrices[data_name].index_names:
                cbox.addItem(str(idx))
            self.table_matrix_list.setCellWidget(i, 1, cbox)

    def find_non_conflicting_name(self, data_name, dictio):
        if data_name in dictio:
            i = 1
            new_data_name = data_name + "_" + str(i)
            while new_data_name in dictio:
                i += 1
                new_data_name = data_name + "_" + str(i)
            data_name = new_data_name
        return data_name

    def change_graph_settings(self):
        for k, v in self.skims.items():
            if not len(v):
                continue
            c = self.traffic_classes[k]  # type: TrafficClass
            graph = c.graph
            graph.set_graph(self.cob_ffttime.currentText())
            graph.set_skimming(v)
            graph.set_blocked_centroid_flows(self.chb_check_centroids.isChecked())
            matrix = c.matrix
            self.traffic_classes[k] = TrafficClass(graph, matrix)

        table = self.tbl_vdf_parameters
        for i in range(table.rowCount()):
            k = table.item(i, 0).text()
            val = table.cellWidget(i, 1).text()
            if len(val) == 0:
                val = table.cellWidget(i, 2).currentText()
            else:
                try:
                    val = float(val)
                except:
                    self.error = 'VDF parameter is not numeric'
                    return False
            self.vdf_parameters[k] = val

        for k, v in self.vdf_parameters.items():
            print(k, v)
        return True

    def exit_procedure(self):
        self.close()
        if self.report:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()

    # def build_query(self, purpose):
    #     # Procedures related to critical analysis. Not yet fully implemented
    #     if purpose == "select link":
    #         button = self.but_build_query
    #         message = "Select Link Analysis"
    #         table = self.select_link_list
    #         counter = self.tot_crit_link_queries
    #     else:
    #         button = self.but_build_query_extract
    #         message = "Link flow extraction"
    #         table = self.list_link_extraction
    #         counter = self.tot_link_flow_extract
    #
    #     button.setEnabled(False)
    #     dlg2 = LoadSelectLinkQueryBuilderDialog(self.iface, self.graph.graph, message)
    #     dlg2.exec_()
    #
    #     if dlg2.links is not None:
    #         table.setRowCount(counter + 1)
    #         text = ""
    #         for i in dlg2.links:
    #             text = text + ", (" + only_str(i[0]) + ', "' + only_str(i[1]) + '")'
    #         text = text[2:]
    #         table.setItem(counter, 0, QTableWidgetItem(text))
    #         table.setItem(counter, 1, QTableWidgetItem(dlg2.query_type))
    #         table.setItem(counter, 2, QTableWidgetItem(dlg2.query_name))
    #         del_button = QPushButton("X")
    #         del_button.clicked.connect(partial(self.click_button_inside_the_list, purpose))
    #         table.setCellWidget(counter, 3, del_button)
    #         counter += 1
    #
    #     if purpose == "select link":
    #         self.tot_crit_link_queries = counter
    #
    #     elif purpose == "Link flow extraction":
    #         self.tot_link_flow_extract = counter
    #
    #     button.setEnabled(True)

    # def load_assignment_queries(self):
    #     # First we load the assignment queries
    #     query_labels = []
    #     query_elements = []
    #     query_types = []
    #     if self.tot_crit_link_queries:
    #         for i in range(self.tot_crit_link_queries):
    #             links = eval(self.select_link_list.item(i, 0).text())
    #             query_type = self.select_link_list.item(i, 1).text()
    #             query_name = self.select_link_list.item(i, 2).text()
    #
    #             for l in links:
    #                 d = directions_dictionary[l[1]]
    #                 lk = self.graph.ids[
    #                     (self.graph.graph["link_id"] == int(l[0])) & (self.graph.graph["direction"] == d)
    #                     ]
    #
    #             query_labels.append(query_name)
    #             query_elements.append(lk)
    #             query_types.append(query_type)
    #
    #     self.critical_queries = {"labels": query_labels, "elements": query_elements, " type": query_types}
    # def set_output_names(self):
    #     self.path_file.temp_file = os.path.join(self.temp_path, "path_file.aed")
    #     self.path_file.output_name = os.path.join(self.output_path, "path_file")
    #     self.path_file.extension = "aed"
    #
    #     if self.do_path_file.isChecked():
    #         self.results.setSavePathFile(save=True, path_result=self.path_file.temp_file)
    #
    #     self.link_extract.temp_file = os.path.join(self.temp_path, "link_extract")
    #     self.link_extract.output_name = os.path.join(self.output_path, "link_extract")
    #     self.link_extract.extension = "aed"
    #
    #     self.critical_output.temp_file = os.path.join(self.temp_path, "critical_output")
    #     self.critical_output.output_name = os.path.join(self.output_path, "critical_output")
    #     self.critical_output.extension = "aed"


class OutputType:
    def __init__(self):
        self.temp_file = None
        self.extension = None
        self.output_name = None

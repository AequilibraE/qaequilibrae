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
 Updated:    30/10/2017
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
from qgis.core import *
import qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt import QtWidgets, uic, QtCore, QtGui
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox, QTableWidgetItem, QAbstractItemView

from aequilibrae.paths import Graph, SkimResults, NetworkSkimming
from aequilibrae.matrix import matrix_export_types
from ..common_tools import GetOutputFileName
from ..common_tools import ReportDialog
from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *

# sys.modules['qgsmaplayercombobox'] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_impedance_matrix.ui"))


class ImpedanceMatrixDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.result = SkimResults()
        self.validtypes = integer_types + float_types
        self.tot_skims = 0
        self.name_skims = 0
        self.graph = None
        self.skimmeable_fields = []
        self.skim_fields = []
        self.error = None
        # FIRST, we connect slot signals

        # For loading a new graph
        self.load_graph_from_file.clicked.connect(self.loaded_new_graph_from_file)

        # For adding skims
        # self.bt_add_skim.clicked.connect(self.add_to_skim_list)
        self.but_adds_to_links.clicked.connect(self.append_to_list)
        self.but_removes_from_links.clicked.connect(self.removes_fields)

        self.do_dist_matrix.clicked.connect(self.run_skimming)

        # SECOND, we set visibility for sections that should not be shown when the form opens (overlapping items)
        #        and re-dimension the items that need re-dimensioning
        self.hide_all_progress_bars()
        self.available_skims_table.setColumnWidth(0, 245)
        self.skim_list.setColumnWidth(0, 245)
        self.available_skims_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.skim_list.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # loads default path from parameters
        self.path = standard_path()

    def removes_fields(self):
        table = self.available_skims_table
        final_table = self.skim_list

        for i in final_table.selectedRanges():
            old_fields = [final_table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                final_table.removeRow(row)

            counter = table.rowCount()
            for field in old_fields:
                table.setRowCount(counter + 1)
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(counter, 0, item1)
                counter += 1

    def append_to_list(self):
        table = self.available_skims_table
        final_table = self.skim_list

        for i in table.selectedRanges():
            new_fields = [table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for f in new_fields:
                self.skim_fields.append(self.only_str(f))
            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                table.removeRow(row)

            counter = final_table.rowCount()
            for field in new_fields:
                final_table.setRowCount(counter + 1)
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                final_table.setItem(counter, 0, item1)
                counter += 1

    def hide_all_progress_bars(self):
        self.progressbar.setVisible(False)
        self.progress_label.setVisible(False)
        self.progressbar.setValue(0)
        self.progress_label.setText("")

    def loaded_new_graph_from_file(self):
        file_types = ["AequilibraE graph(*.aeg)"]

        new_name, file_type = GetOutputFileName(self, "Graph file", file_types, ".aeg", self.path)
        self.cb_minimizing.clear()
        self.available_skims_table.clearContents()
        self.block_paths.setChecked(False)
        self.graph = None
        if new_name is not None:
            self.graph_file_name.setText(new_name)
            self.graph = Graph()
            self.graph.load_from_disk(new_name)

            self.block_paths.setChecked(self.graph.block_centroid_flows)
            self.skimmeable_fields = self.graph.available_skims()

            self.available_skims_table.setRowCount(len(self.skimmeable_fields))
            for i, q in enumerate(self.skimmeable_fields):
                self.cb_minimizing.addItem(q)
                self.available_skims_table.setItem(i, 0, QTableWidgetItem(q))

    def browse_outfile(self):
        self.imped_results = None
        new_name, extension = GetOutputFileName(
            self, "AequilibraE impedance computation", matrix_export_types, ".aem", self.path
        )
        if new_name is not None:
            self.imped_results = new_name

    def run_thread(self):
        self.do_dist_matrix.setVisible(False)
        self.progressbar.setRange(0, self.graph.num_zones)
        self.worker_thread.skimming.connect(self.signal_handler)
        self.worker_thread.start()
        self.exec_()

    def signal_handler(self, val):
        if val[0] == "zones finalized":
            self.progressbar.setValue(val[1])
        elif val[0] == "text skimming":
            self.progress_label.setText(val[1])
        elif val[0] == "finished_threaded_procedure":
            self.finished_threaded_procedure()

    def finished_threaded_procedure(self):
        self.report = self.worker_thread.report
        self.result.skims.export(self.only_str(self.imped_results))
        self.exit_procedure()

    def run_skimming(self):  # Saving results

        if self.error is None:
            self.browse_outfile()
            cost_field = self.cb_minimizing.currentText()

            # We prepare the graph to set all nodes as centroids
            if self.rdo_all_nodes.isChecked():
                self.graph.prepare_graph(self.graph.all_nodes)

            self.graph.set_graph(
                cost_field=cost_field, skim_fields=self.skim_fields, block_centroid_flows=self.block_paths.isChecked()
            )

            self.result.prepare(self.graph)

            self.funding1.setVisible(False)
            self.funding2.setVisible(False)
            self.progressbar.setVisible(True)
            self.progress_label.setVisible(True)
            self.worker_thread = NetworkSkimming(self.graph, self.result)
            try:
                self.run_thread()
            except ValueError as error:
                qgis.utils.iface.messageBar().pushMessage("Input error", error.message, level=3)
        else:
            qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=3)

    @staticmethod
    def only_str(str_input):
        if isinstance(str_input, bytes):
            return str_input.decode("utf-8")
        return str_input

    def check_inputs(self):
        self.error = None
        if self.rdo_all_nodes.isChecked() and self.block_paths.isChecked():
            self.error = "It is not possible to trace paths between all nodes while blocking flows through centroids"

        if self.graph is None:
            self.error = "No graph loaded"

        if len(self.skim_fields) < 1:
            self.error = "No skim fields provided"

    def exit_procedure(self):
        self.close()
        if self.report:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()

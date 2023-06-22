import importlib.util as iutil
import os
from os.path import join

import pandas as pd
from qgis._core import QgsProject, QgsVectorLayer, QgsDataSourceUri

import qgis
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QAbstractItemView
from .display_aequilibrae_formats_dialog import DisplayAequilibraEFormatsDialog
from .load_result_table import load_result_table
from .matrix_lister import list_matrices
from .results_lister import list_results
from ..common_tools import PandasModel

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_project_data.ui"))

# Checks if we can display OMX
spec = iutil.find_spec("openmatrix")
has_omx = spec is not None


class LoadProjectDataDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgs_proj):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgs_proj.iface
        self.setupUi(self)
        self.data_to_show = None
        self.error = None
        self.qgs_proj = qgs_proj
        self.project = qgs_proj.project

        self.matrices: pd.DataFrame = None
        self.matrices_model: PandasModel = None

        self.results: pd.DataFrame = None
        self.results_model: PandasModel = None

        for table in [self.list_matrices, self.list_results]:
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.load_matrices()
        self.load_results()

        self.but_update_matrices.clicked.connect(self.update_matrix_table)
        self.but_load_Results.clicked.connect(self.load_result_table)
        self.but_load_matrix.clicked.connect(self.display_matrix)

    def display_matrix(self):
        idx = [x.row() for x in list(self.list_matrices.selectionModel().selectedRows())]
        if not idx:
            return
        if self.matrices["WARNINGS"][idx[0]] != "":
            return

        file_name = self.matrices["file_name"][idx[0]]

        dlg2 = DisplayAequilibraEFormatsDialog(self.qgs_proj, join(self.project.matrices.fldr, file_name), proj=True)
        dlg2.show()
        dlg2.exec_()

    def load_matrices(self):

        self.matrices = list_matrices(self.project.matrices.fldr)

        self.matrices_model = PandasModel(self.matrices)
        self.list_matrices.setModel(self.matrices_model)

    def update_matrix_table(self):
        matrices = self.project.matrices
        matrices.update_database()
        self.load_matrices()

    def load_results(self):
        self.results = list_results(self.project.project_base_path)

        self.results_model = PandasModel(self.results)
        self.list_results.setModel(self.results_model)

    def load_result_table(self):
        idx = [x.row() for x in list(self.list_results.selectionModel().selectedRows())]
        if not idx:
            return
        table_name = self.results["table_name"][idx[0]]
        if self.results["WARNINGS"][idx[0]] != "":
            return

        _ = load_result_table(self.project.project_base_path, table_name)

    def exit_with_error(self):
        qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1)
        self.close()

    def exit_procedure(self):
        self.show()
        self.close()
        # sys.exit(app.exec_())

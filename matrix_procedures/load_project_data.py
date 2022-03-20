import importlib.util as iutil
import os
import sqlite3
from os.path import join

import pandas as pd
from aequilibrae.project.database_connection import database_connection
from qgis._core import QgsProject, QgsVectorLayer, QgsDataSourceUri

import qgis
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QAbstractItemView
from .display_aequilibrae_formats_dialog import DisplayAequilibraEFormatsDialog
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
        if self.matrices['WARNINGS'][idx[0]] != '':
            return

        file_name = self.matrices['file_name'][idx[0]]

        dlg2 = DisplayAequilibraEFormatsDialog(self.iface, join(self.project.matrices.fldr, file_name))
        dlg2.show()
        dlg2.exec_()

    def load_matrices(self):

        conn = database_connection()
        df = pd.read_sql('select * from matrices', conn)
        conn.close()

        fldr = self.project.matrices.fldr
        existing_files = os.listdir(fldr)

        self.matrices = df.assign(WARNINGS='')
        for idx, record in self.matrices.iterrows():
            if record.file_name not in existing_files:
                self.matrices.loc[idx, 'WARNINGS'] = 'File not found on disk'

            elif record.file_name[-4:] == '.omx' and not has_omx:
                self.matrices.loc[idx, 'WARNINGS'] = 'OMX not available for display'

        self.matrices_model = PandasModel(self.matrices)
        self.list_matrices.setModel(self.matrices_model)

    def update_matrix_table(self):
        matrices = self.project.matrices
        matrices.update_database()
        self.load_matrices()

    def load_results(self):
        conn = database_connection()
        df = pd.read_sql('select * from results', conn)
        conn.close()

        conn = sqlite3.connect(join(self.project.project_base_path, 'results_database.sqlite'))
        tables = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
        conn.close()
        self.results = df.assign(WARNINGS='')
        for idx, record in self.results.iterrows():
            if record.table_name not in tables:
                self.results.loc[idx, 'WARNINGS'] = 'Table not found in the results database'

        self.results_model = PandasModel(self.results)
        self.list_results.setModel(self.results_model)

    def load_result_table(self):
        idx = [x.row() for x in list(self.list_results.selectionModel().selectedRows())]
        if not idx:
            return
        table_name = self.results['table_name'][idx[0]]
        if self.results['WARNINGS'][idx[0]] != '':
            return

        pth = join(self.project.project_base_path, 'results_database.sqlite')
        conn = qgis.utils.spatialite_connect(pth)
        conn.execute('PRAGMA temp_store = 0;')
        conn.execute('SELECT InitSpatialMetaData();')
        conn.commit()
        conn.close()

        uri = QgsDataSourceUri()
        uri.setDatabase(pth)
        uri.setDataSource('', table_name, None)
        lyr = QgsVectorLayer(uri.uri(), table_name, 'spatialite')
        QgsProject.instance().addMapLayer(lyr)
        # layer_from_dataframe(df, table_name)

    def exit_with_error(self):
        qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1)
        self.close()

    def exit_procedure(self):
        self.show()
        self.close()
        # sys.exit(app.exec_())

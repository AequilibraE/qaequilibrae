"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Trip distribution models
 Purpose:    Loads GUI for all of AequilibraE's distribution model procedures

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-10-02
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, uic
from collections import OrderedDict
from functools import partial
import numpy as np
import os
import yaml
from ..matrix_procedures import LoadMatrixDialog
from ..common_tools.auxiliary_functions import *
from ..common_tools import ReportDialog
from calibrate_gravity_procedure import CalibrateGravityProcedure
from ..common_tools.get_output_file_name import GetOutputFileName
from ..aequilibrae.matrix import AequilibraEData, AequilibraeMatrix

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_distribution.ui'))


class DistributionModelsDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, mode=None):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.error = None
        self.report = None

        self.matrices = OrderedDict()
        self.datasets = OrderedDict()
        self.job = None

        self.model_tabs.setVisible(False)
        self.resize(239, 120)
        self.rdo_ipf.clicked.connect(self.configure_inputs)
        self.rdo_apply_gravity.clicked.connect(self.configure_inputs)
        self.rdo_calibrate_gravity.clicked.connect(self.configure_inputs)

        self.but_load_data.clicked.connect(self.load_datasets)
        self.but_load_mat.clicked.connect(self.load_matrices)

        self.cob_prod_data.currentIndexChanged.connect(partial(self.change_vector_field,
                                                               self.cob_prod_data, self.cob_prod_field, "data"))
        self.cob_atra_data.currentIndexChanged.connect(partial(self.change_vector_field,
                                                               self.cob_atra_data, self.cob_atra_field, "data"))

        self.cob_imped_mat.currentIndexChanged.connect(partial(self.change_vector_field,
                                                               self.cob_imped_mat, self.cob_imped_field, "matrix"))
        self.cob_seed_mat.currentIndexChanged.connect(partial(self.change_vector_field,
                                                              self.cob_seed_mat, self.cob_seed_field, "matrix"))

        self.but_run.clicked.connect(self.run)

        if mode is not None:
            if mode == "ipf":
                self.rdo_ipf.setChecked(True)
            if mode == "apply":
                self.rdo_apply_gravity.setChecked(True)
            if mode == "calibrate":
                self.rdo_calibrate_gravity.setChecked(True)

    def configure_inputs(self):
        self.resize(452, 334)
        self.model_tabs.setEnabled(True)
        self.model_tabs.setVisible(True)

        if self.rdo_ipf.isChecked():
            self.job = 'ipf'
            self.model_tabs.setTabText(4, "Seed matrix")
            self.model_tabs.removeTab(6)
            self.model_tabs.removeTab(5)
            self.model_tabs.removeTab(3)

        if self.rdo_apply_gravity.isChecked():
            self.job = 'apply'
            self.model_tabs.removeTab(6)
            self.model_tabs.removeTab(4)

        if self.rdo_calibrate_gravity.isChecked():
            self.job = 'calibrate'
            self.model_tabs.setTabText(4, "Observed matrix")
            self.model_tabs.removeTab(5)
            self.model_tabs.removeTab(2)
            self.model_tabs.removeTab(0)
            self.rdo_gamma.setEnabled(False)
            self.rdo_friction.setEnabled(False)

        self.rdo_ipf.setEnabled(False)
        self.rdo_apply_gravity.setEnabled(False)
        self.rdo_calibrate_gravity.setEnabled(False)

    def load_datasets(self):
        dataset_name = self.browse_outfile('aed')

        if dataset_name is not None:
            try:
                dataset = AequilibraEData()
                dataset.load(dataset_name)

                data_name = os.path.splitext(os.path.basename(dataset_name))[0]
                data_name = self.find_non_conflicting_name(data_name, self.datasets)
                self.datasets[data_name] = dataset
                self.add_to_table(self.datasets, self.table_datasets)
                self.load_comboboxes(self.datasets.keys(), self.cob_prod_data)
                self.load_comboboxes(self.datasets.keys(), self.cob_atra_data)
                logger(1)
            except:
                self.error = 'Could not load file. It might be corrupted or might not be a valid AequilibraE file'

    def load_matrices(self):
        matrix_name = self.browse_outfile('aem')

        if matrix_name is not None:
            try:
                matrix = AequilibraeMatrix()
                matrix.load(matrix_name)

                matrix_name = os.path.splitext(os.path.basename(matrix_name))[0]
                matrix_name = self.find_non_conflicting_name(matrix_name, self.matrices)
                self.matrices[matrix_name] = matrix
                self.add_to_table(self.matrices, self.table_matrices)
                self.load_comboboxes(self.matrices.keys(), self.cob_imped_mat)
                self.load_comboboxes(self.matrices.keys(), self.cob_seed_mat)

            except:
                self.error = 'Could not load file. It might be corrupted or might not be a valid AequilibraE file'

    def change_vector_field(self, cob_orig, cob_dest, dt):
        cob_dest.clear()
        d = str(cob_orig.currentText())
        if len(d) > 0:
            if dt == "data":
                for f in self.datasets[d].fields:
                    if np.issubdtype(self.datasets[d].data[f].dtype, np.integer) or \
                            np.issubdtype(self.datasets[d].data[f].dtype, np.float):
                        cob_dest.addItem(f)
            else:
                for f in self.matrices[d].names:
                    cob_dest.addItem(f)

    def load_comboboxes(self, list_to_load, data_cob):
        data_cob.clear()
        for d in list_to_load:
            data_cob.addItem(d)

    def find_non_conflicting_name(self, data_name, dictio):
        if data_name in dictio:
            i = 1
            new_data_name = data_name + '_' + str(i)
            while new_data_name in dictio:
                i += 1
                new_data_name = data_name + '_' + str(i)
            data_name = new_data_name
        return data_name

    def add_to_table(self, dictio, table):
        table.setColumnWidth(0, 190)
        table.setColumnWidth(1, 80)
        table.clearContents()
        table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.count = table.setRowCount(len(dictio.keys()))

        for i, data_name in enumerate(dictio.keys()):
            table.setItem(i, 0, QTableWidgetItem(data_name))
            if isinstance(dictio[data_name], AequilibraEData):
                table.setItem(i, 1, QTableWidgetItem(str(dictio[data_name].num_fields)))
            else:
                table.setItem(i, 1, QTableWidgetItem(str(dictio[data_name].cores)))

    def browse_outfile(self, file_type):

        file_types = {'aed': ['AequilibraE dataset', "Aequilibrae dataset(*.aed)", '.aed'],
                      'mod': ['Model file', 'Model file(*.mod)', '.mod'],
                      'aem': ['AequilibraE matrix', "Aequilibrae matrix(*.aem)", '.aem']}

        ft = file_types[file_type]
        file_chosen, _ = GetOutputFileName(self, ft[0], [ft[1]], ft[2], self.path)
        return file_chosen

    def run(self):
        if self.check_data():
            pass
            # self.worker_thread = CalibrateGravityProcedure(qgis.utils.iface.mainWindow(), self.observed, self.impedance,
            #                                                self.function)
            # self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input error", self.error, level=3)

    def check_data(self):
        self.error = None

        if self.job != 'calibrate':
            if self.cob_prod_field.currentIndex() < 0:
                self.error = 'Production vector is missing'

            if self.cob_atra_field.currentIndex() < 0:
                self.error = 'Attraction vector is missing'

        if self.job != 'apply':
            if self.cob_seed_field.currentIndex() < 0:
                self.error = 'Observed (seed) matrix is missing'

        if self.job != 'ipf':
            if self.cob_imped_field.currentIndex() < 0:
                self.error = 'Impedance matrix is missing'

        # if self.result_file is None:
        #     self.error = 'Parameters for output missing'

        if self.error is not None:
            return False
        else:
            return True

    def run_thread(self):
        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"),
                        self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.job_finished_from_thread)
        self.worker_thread.start()
        self.exec_()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val[1])

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value[1])

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value[1])

    def job_finished_from_thread(self, success):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Procedure error: ", self.worker_thread.error, level=3)
        else:
            self.report = self.worker_thread.gravity.report
            stream = open(self.result_file, 'w')
            yaml.dump(self.worker_thread.gravity.model, stream, default_flow_style=False)
            stream.close()

        self.exit_procedure()

    def exit_procedure(self):
        self.close()
        if self.report is not None:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()

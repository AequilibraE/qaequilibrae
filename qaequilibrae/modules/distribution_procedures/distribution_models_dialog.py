import importlib.util as iutil
import os
from collections import OrderedDict
from functools import partial
from os.path import join

import numpy as np
from aequilibrae.distribution import SyntheticGravityModel
from aequilibrae.distribution.synthetic_gravity_model import valid_functions
from aequilibrae.matrix import AequilibraeData, AequilibraeMatrix

from qgis.PyQt.QtWidgets import QAbstractItemView
from qaequilibrae.modules.matrix_procedures.matrix_lister import list_matrices
from qaequilibrae.modules.common_tools import PandasModel
import qgis
from aequilibrae.context import get_logger
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QTableWidgetItem, QComboBox, QDoubleSpinBox, QAbstractItemView
from qaequilibrae.modules.distribution_procedures.apply_gravity_procedure import ApplyGravityProcedure
from qaequilibrae.modules.distribution_procedures.calibrate_gravity_procedure import CalibrateGravityProcedure
from qaequilibrae.modules.distribution_procedures.ipf_procedure import IpfProcedure
from qaequilibrae.modules.common_tools import GetOutputFileName
from qaequilibrae.modules.common_tools import ReportDialog
from qaequilibrae.modules.common_tools.auxiliary_functions import standard_path
from qaequilibrae.modules.matrix_procedures import LoadDatasetDialog, DisplayAequilibraEFormatsDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_distribution.ui"))
spec = iutil.find_spec("openmatrix")
has_omx = spec is not None


# TODO: Implement consideration of the "empty as zeros" for ALL distrbution models Should force inputs for trip distribution to be of FLOAT type

logger = get_logger()


class DistributionModelsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgs_proj, mode=None):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgs_proj.iface
        self.setupUi(self)
        self.path = standard_path()

        self.qgs_proj = qgs_proj
        self.project = qgs_proj.project

        self.error = None
        self.report = []
        self.job_queue = OrderedDict()
        self.model = SyntheticGravityModel()
        self.model.function = "GAMMA"
        self.outfile = ""

        self.matrices = OrderedDict()
        self.datasets = OrderedDict()
        self.job = mode

        self.model_tabs.setVisible(False)
        self.resize(239, 120)
        self.rdo_ipf.clicked.connect(self.configure_inputs)
        self.rdo_apply_gravity.clicked.connect(self.configure_inputs)
        self.rdo_calibrate_gravity.clicked.connect(self.configure_inputs)

        self.but_load_data.clicked.connect(self.load_datasets)
        self.but_load_model.clicked.connect(self.load_model)

        self.cob_prod_data.currentIndexChanged.connect(
            partial(self.change_vector_field, self.cob_prod_data, self.cob_prod_field, "data")
        )
        self.cob_atra_data.currentIndexChanged.connect(
            partial(self.change_vector_field, self.cob_atra_data, self.cob_atra_field, "data")
        )

        self.cob_imped_mat.currentIndexChanged.connect(
            partial(self.change_vector_field, self.cob_imped_mat, self.cob_imped_field, "matrix")
        )
        self.cob_seed_mat.currentIndexChanged.connect(
            partial(self.change_vector_field, self.cob_seed_mat, self.cob_seed_field, "matrix")
        )

        self.but_run.clicked.connect(self.run)
        self.but_queue.clicked.connect(self.add_job_to_queue)
        self.but_cancel.clicked.connect(self.close)
        self.table_datasets.doubleClicked.connect(self.data_double_clicked)

        self.table_jobs.setColumnWidth(0, 50)
        self.table_jobs.setColumnWidth(1, 295)
        self.table_jobs.setColumnWidth(2, 90)

        self.but_run.setVisible(False)
        self.but_queue.setVisible(False)
        self.but_cancel.setVisible(False)

        if mode is not None:
            if mode == "ipf":
                self.rdo_ipf.setChecked(True)
            if mode == "apply":
                self.rdo_apply_gravity.setChecked(True)
            if mode == "calibrate":
                self.rdo_calibrate_gravity.setChecked(True)
            self.configure_inputs()

        self.load_matrices()
        self.user_chosen_model = None
        self.update_model_parameters()

    def load_matrices(self):
        self.matrices = list_matrices(self.project.matrices.fldr)

        self.matrices_model = PandasModel(self.matrices)
        self.list_matrices.setModel(self.matrices_model)
        self.cob_imped_mat.addItems(self.matrices["name"].tolist())
        self.cob_seed_mat.addItems(self.matrices["name"].tolist())

    def data_double_clicked(self, mi):
        row = mi.row()
        if row > -1:
            obj_to_view = self.table_datasets.item(row, 0).text()
            dlg2 = DisplayAequilibraEFormatsDialog(self.iface, self.datasets[obj_to_view])
            dlg2.show()
            dlg2.exec_()

    def configure_inputs(self):
        self.but_run.setVisible(True)
        self.but_queue.setVisible(True)
        self.but_cancel.setVisible(True)

        self.resize(511, 334)
        self.model_tabs.setEnabled(True)
        self.model_tabs.setVisible(True)
        to_remove = []
        if self.rdo_ipf.isChecked():
            self.job = "ipf"
            self.setWindowTitle(self.tr("AequilibraE - Iterative Proportional Fitting"))
            self.model_tabs.setTabText(4, self.tr("Seed matrix"))
            to_remove = [6, 5, 3]

        if self.rdo_apply_gravity.isChecked():
            self.setWindowTitle(self.tr("AequilibraE - Apply gravity model"))
            self.job = "apply"
            to_remove = [6, 4]

        if self.rdo_calibrate_gravity.isChecked():
            self.job = "calibrate"
            self.setWindowTitle(self.tr("AequilibraE - Calibrate gravity model"))
            self.model_tabs.setTabText(4, self.tr("Observed matrix"))
            to_remove = [5, 2, 0]
            self.rdo_gamma.setEnabled(False)
            self.rdo_friction.setEnabled(False)

        for i in to_remove:
            self.model_tabs.removeTab(i)

        self.rdo_ipf.setEnabled(False)
        self.rdo_apply_gravity.setEnabled(False)
        self.rdo_calibrate_gravity.setEnabled(False)

    def change_model_by_user(self):
        self.model.function = self.user_chosen_model.currentText()
        self.update_model_parameters()

    def update_model_parameters(self):
        self.user_chosen_model = QComboBox()
        for f in valid_functions:
            self.user_chosen_model.addItem(f)
        # self.user_chosen_model.blockSignals(True)
        self.user_chosen_model.setCurrentIndex(valid_functions.index(self.model.function))
        # self.user_chosen_model.blockSignals(False)
        self.user_chosen_model.currentIndexChanged.connect(self.change_model_by_user)

        self.table_model.setRowCount(2)
        self.table_model.setItem(0, 0, QTableWidgetItem(self.tr("Function")))

        self.table_model.setCellWidget(0, 1, self.user_chosen_model)

        i = 2
        if self.model.function in ["POWER", "GAMMA"]:
            i = 3
            self.table_model.setItem(1, 0, QTableWidgetItem("Alpha"))
            val = self.model.alpha
            if val is None:
                val = 0
            item0 = QDoubleSpinBox()
            item0.setMinimum(-5000)
            item0.setMaximum(5000)
            item0.setDecimals(7)
            item0.setValue(float(val))
            self.table_model.setCellWidget(1, 1, item0)

        if self.model.function in ["EXPO", "GAMMA"]:
            self.table_model.setRowCount(i)
            self.table_model.setItem(i - 1, 0, QTableWidgetItem("Beta"))
            val = self.model.beta
            if val is None:
                val = 0
            item = QDoubleSpinBox()
            item.setMinimum(-5000)
            item.setMaximum(5000)

            item.setDecimals(7)
            item.setValue(float(val))
            self.table_model.setCellWidget(i - 1, 1, item)

    def load_datasets(self):
        dlg2 = LoadDatasetDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if isinstance(dlg2.dataset, AequilibraeData):
            dataset_name = dlg2.dataset.file_path
            if dataset_name is not None:
                data_name = os.path.splitext(os.path.basename(dataset_name))[0]
                data_name = self.find_non_conflicting_name(data_name, self.datasets)
                self.datasets[data_name] = dlg2.dataset
                self.add_to_table(self.datasets, self.table_datasets)
                self.load_comboboxes(self.datasets.keys(), self.cob_prod_data)
                self.load_comboboxes(self.datasets.keys(), self.cob_atra_data)

    def load_model(self):
        file_name = self.browse_outfile("mod")
        try:
            self.model.load(file_name)
            self.update_model_parameters()
        except Exception as e:
            qgis.utils.iface.messageBar().pushMessage(
                "Error", self.tr("Could not load model. {}").format(e.args), level=3, duration=10
            )

    def change_vector_field(self, cob_orig, cob_dest, dt):
        cob_dest.clear()
        d = str(cob_orig.currentText())
        if len(d) > 0:
            if dt == "data":
                for f in self.datasets[d].fields:
                    if np.issubdtype(self.datasets[d].data[f].dtype, np.integer) or np.issubdtype(
                        self.datasets[d].data[f].dtype, np.float64
                    ):
                        cob_dest.addItem(f)
            else:
                file_name = self.matrices.at[cob_orig.currentIndex(), "file_name"]
                mat = AequilibraeMatrix()
                mat.load(join(self.project.matrices.fldr, file_name))
                cob_dest.addItems(mat.names)

    def load_comboboxes(self, list_to_load, data_cob):
        data_cob.clear()
        for d in list_to_load:
            data_cob.addItem(d)

    def find_non_conflicting_name(self, data_name, dictio):
        if data_name in dictio:
            i = 1
            new_data_name = data_name + "_" + str(i)
            while new_data_name in dictio:
                i += 1
                new_data_name = data_name + "_" + str(i)
            data_name = new_data_name
        return data_name

    def add_to_table(self, dictio, table):
        table.setColumnWidth(0, 235)
        table.setColumnWidth(1, 80)
        table.clearContents()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setRowCount(len(dictio.keys()))

        for i, data_name in enumerate(dictio.keys()):
            table.setItem(i, 0, QTableWidgetItem(data_name))
            if isinstance(dictio[data_name], AequilibraeData):
                table.setItem(i, 1, QTableWidgetItem(str(dictio[data_name].num_fields)))
            else:
                table.setItem(i, 1, QTableWidgetItem(str(dictio[data_name].cores)))

    def browse_outfile(self, file_type):
        file_types = {
            "aed": ["AequilibraE dataset", ["Aequilibrae dataset(*.aed)"], ".aed"],
            "mod": ["Model file", ["Model file(*.mod)"], ".mod"],
            "aem": ["Matrix", ["Aequilibrae matrix(*.aem)"], ".aem"],
        }

        if has_omx:
            file_types["aem"] = ["Matrix", ["Open Matrix(*.omx)", "Aequilibrae matrix(*.aem)"], ".omx"]

        ft = file_types[file_type]
        file_chosen, _ = GetOutputFileName(self, ft[0], ft[1], ft[2], self.path)
        return file_chosen

    def add_job_to_queue(self):
        worker_thread = None
        if self.check_data():
            if self.job != "ipf":
                imped_name = self.matrices.at[self.cob_imped_mat.currentIndex(), "file_name"]
                imped_matrix = AequilibraeMatrix()
                imped_matrix.load(join(self.project.matrices.fldr, imped_name))
                imped_matrix.computational_view([self.cob_imped_field.currentText()])

            if self.job != "apply":
                seed_name = self.matrices.at[self.cob_seed_mat.currentIndex(), "file_name"]
                seed_matrix = AequilibraeMatrix()
                seed_matrix.load(join(self.project.matrices.fldr, seed_name))
                seed_matrix.computational_view([self.cob_seed_field.currentText()])

            if self.job != "calibrate":
                prod_vec = self.datasets[self.cob_prod_data.currentText()]
                prod_field = self.cob_prod_field.currentText()
                atra_vec = self.datasets[self.cob_atra_data.currentText()]
                atra_field = self.cob_atra_field.currentText()

            if self.job == "ipf":
                self.out_name = self.browse_outfile("aem")
                if self.out_name is not None:
                    args = {
                        "matrix": seed_matrix,
                        "rows": prod_vec,
                        "row_field": prod_field,
                        "columns": atra_vec,
                        "column_field": atra_field,
                        "nan_as_zero": self.chb_empty_as_zero.isChecked(),
                    }
                    worker_thread = IpfProcedure(qgis.utils.iface.mainWindow(), **args)

            if self.job == "apply":
                self.out_name = self.browse_outfile("aem")
                if self.out_name is not None:
                    for i in range(1, self.table_model.rowCount()):
                        if str(self.table_model.item(i, 0).text()) == "Alpha":
                            self.model.alpha = float(self.table_model.cellWidget(i, 1).value())
                        if str(self.table_model.item(i, 0).text()) == "Beta":
                            self.model.beta = float(self.table_model.cellWidget(i, 1).value())

                    args = {
                        "impedance": imped_matrix,
                        "rows": prod_vec,
                        "row_field": prod_field,
                        "model": self.model,
                        "columns": atra_vec,
                        "column_field": atra_field,
                        "output": self.out_name,
                        "nan_as_zero": self.chb_empty_as_zero.isChecked(),
                    }
                    worker_thread = ApplyGravityProcedure(qgis.utils.iface.mainWindow(), **args)

            if self.job == "calibrate":
                self.out_name = self.browse_outfile("mod")
                if self.out_name is not None:
                    if self.rdo_expo.isChecked():
                        func_name = "EXPO"
                    if self.rdo_power.isChecked():
                        func_name = "POWER"
                    if self.rdo_gamma.isChecked():
                        func_name = "GAMMA"
                    if self.rdo_friction.isChecked():
                        func_name = "FRICTION"

                    args = {
                        "matrix": imped_matrix,
                        "impedance": imped_matrix,
                        "function": func_name,
                        "nan_as_zero": self.chb_empty_as_zero.isChecked(),
                    }
                    worker_thread = CalibrateGravityProcedure(qgis.utils.iface.mainWindow(), **args)

            self.chb_empty_as_zero.setEnabled(False)
            if worker_thread is None:
                return
            self.add_job_to_list(worker_thread, self.out_name)
        else:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Procedure error: "), self.error, level=3)

    def add_job_to_list(self, job, out_name):
        self.job_queue[out_name] = job

        self.table_jobs.clearContents()
        self.table_jobs.setRowCount(len(self.job_queue.keys()))

        for i, j in enumerate(self.job_queue.keys()):
            data_name = os.path.splitext(os.path.basename(j))[0]
            self.table_jobs.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table_jobs.setItem(i, 1, QTableWidgetItem(data_name))
            self.table_jobs.setItem(i, 2, QTableWidgetItem(self.tr("Queued")))

    def run(self):
        self.chb_empty_as_zero.setVisible(False)
        try:
            for out_name in self.job_queue.keys():
                self.outfile = out_name
                self.worker_thread = self.job_queue[self.outfile]
                self.run_thread()
        except Exception as e:
            logger.error(e.args)

    def check_data(self):
        self.error = None

        # Check for missing info
        if self.job != "calibrate":
            if self.cob_prod_field.currentIndex() < 0:
                self.error = self.tr("Production vector is missing")

            if self.cob_atra_field.currentIndex() < 0:
                self.error = self.tr("Attraction vector is missing")

        if self.job != "apply":
            if self.cob_seed_field.currentIndex() < 0:
                self.error = self.tr("Observed (seed) matrix is missing")

        if self.job != "ipf":
            if self.cob_imped_field.currentIndex() < 0:
                self.error = self.tr("Impedance matrix is missing")

        if self.error is not None:
            return False
        else:
            return True

    def run_thread(self):
        self.worker_thread.jobFinished.connect(self.job_finished_from_thread)
        self.worker_thread.doWork()
        self.show()

    def job_finished_from_thread(self, val):
        error = self.worker_thread.error
        if error is not None:
            qgis.utils.iface.messageBar().pushMessage(self.tr("Procedure error: "), error.args[0], level=3)
        self.report.extend(self.worker_thread.report)

        if val[3] == "calibrate":
            self.worker_thread.model.save(self.outfile)

        if val[3] in ["apply_gravity", "finishedIPF"]:
            self.worker_thread.output.export(self.outfile)
        self.exit_procedure()

    def exit_procedure(self):
        if self.report is not None:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()
        self.close()

from collections import OrderedDict
from functools import partial
from os.path import basename, dirname, join, splitext
from typing import Any

import numpy as np
import pandas as pd
import qgis
from aequilibrae.distribution import SyntheticGravityModel
from aequilibrae.distribution.synthetic_gravity_model import valid_functions
from aequilibrae.matrix import AequilibraeMatrix
from qgis.PyQt.QtWidgets import QTableWidgetItem, QComboBox, QDoubleSpinBox, QAbstractItemView
from qgis.core import (
    QgsApplication,
    QgsProcessingAlgRunnerTask,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
)

from qaequilibrae.modules.common_tools import PandasModel, ReportDialog, GetOutputFileName, BaseDialog
from qaequilibrae.modules.common_tools.auxiliary_functions import standard_path
from qaequilibrae.modules.matrix_procedures import LoadDatasetDialog
from qaequilibrae.modules.matrix_procedures.matrix_lister import list_matrices
from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe
from qaequilibrae.qgis_logging import get_logger

# TODO: Implement consideration of the "empty as zeros" for ALL distrbution models Should force inputs for trip distribution to be of FLOAT type

logger = get_logger(__name__)


class DistributionModelsDialog(BaseDialog):
    def __init__(self, qgis_project, mode=None):
        super().__init__(
            ui_file=join(dirname(__file__), "forms/ui_distribution.ui"), qgis_project=qgis_project, mode=mode
        )

    def _base_ui_setup(self, **kwargs):
        mode = kwargs.get("mode")
        self.path = standard_path()

        self.error = None
        self.job_queue = OrderedDict()
        self.model = SyntheticGravityModel()
        self.model.function = "GAMMA"
        self.outfile = ""
        self._task = None
        self._task_context = None
        self._task_feedback = None
        self._task_layer = None
        self._pending_jobs = []

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

        self.cob_data.currentIndexChanged.connect(
            partial(self.change_vector_field, self.cob_data, self.cob_index, "data")
        )
        self.cob_data.currentIndexChanged.connect(
            partial(self.change_vector_field, self.cob_data, self.cob_prod_field, "data")
        )
        self.cob_data.currentIndexChanged.connect(
            partial(self.change_vector_field, self.cob_data, self.cob_atra_field, "data")
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
        self.matrices = list_matrices(self.project)

        self.matrices_model = PandasModel(self.matrices)
        self.list_matrices.setModel(self.matrices_model)
        self.cob_imped_mat.addItems(self.matrices["name"].tolist())
        self.cob_seed_mat.addItems(self.matrices["name"].tolist())

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
        self.user_chosen_model.setCurrentIndex(valid_functions.index(self.model.function))
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
        dlg2 = LoadDatasetDialog(self.qgis_project)
        dlg2.show()
        dlg2.exec()
        if isinstance(dlg2.dataset, pd.DataFrame):
            dataset_name = dlg2.output_name
            if dataset_name is not None:
                data_name = splitext(basename(dataset_name))[0]
                data_name = self.find_non_conflicting_name(data_name, self.datasets)
                self.datasets[data_name] = dlg2.dataset
                self.add_to_table(self.datasets, self.table_datasets)
                self.load_comboboxes(self.datasets.keys(), self.cob_data)
            # To use a QGIS layer as input, we deactivate part of the widgets
            self._has_idx = True if dlg2.radio_layer.isChecked() else False
            if self._has_idx:
                self.cob_index.clear()
                self.cob_index.setEnabled(False)
        else:
            self.qgis_project.iface_warning_message(self.tr("You need to load a dataset to proceed"))

    def load_model(self):
        file_name = self.browse_outfile("mod")
        if not file_name:
            return
        try:
            self.model.load(file_name)
            self.update_model_parameters()
        except Exception as e:
            self.qgis_project.iface_error_message(self.tr("Could not load model. {}").format(e.args))

    def change_vector_field(self, cob_orig, cob_dest, dt):
        cob_dest.clear()
        d = str(cob_orig.currentText())
        if len(d) > 0:
            if dt == "data":
                for f in self.datasets[d].columns:
                    if np.issubdtype(self.datasets[d][f].dtype, np.integer) or np.issubdtype(
                        self.datasets[d][f].dtype, np.float64
                    ):
                        cob_dest.addItem(f)
            else:
                file_name = self.matrices.at[cob_orig.currentIndex(), "file_name"]
                mat = AequilibraeMatrix()
                mat.load(self.project.project_base_path / "matrices" / file_name)
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
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setRowCount(len(dictio.keys()))

        for i, data_name in enumerate(dictio.keys()):
            table.setItem(i, 0, QTableWidgetItem(data_name))
            if isinstance(dictio[data_name], pd.DataFrame):
                table.setItem(i, 1, QTableWidgetItem(str(dictio[data_name].shape[1] - 1)))
            else:
                table.setItem(i, 1, QTableWidgetItem(str(dictio[data_name].cores)))

    def browse_outfile(self, file_type):
        file_types = {
            "mod": ["Model file", ["Model file(*.mod)"], ".mod"],
            "omx": ["Matrix", ["Open matrix(*.omx)"], ".omx"],
        }

        ft = file_types[file_type]
        file_chosen, _ = GetOutputFileName(self, ft[0], ft[1], ft[2], self.path)
        return file_chosen

    def add_job_to_queue(self):
        if not self.check_data():
            self.qgis_project.iface_error_message(self.error, self.tr("Procedure error: "))
            return

        job = {"kind": self.job, "nan_as_zero": self.chb_empty_as_zero.isChecked()}

        if self.job != "ipf":
            job["impedance_name"] = self.matrices.at[self.cob_imped_mat.currentIndex(), "name"]
            job["impedance_core"] = self.cob_imped_field.currentText()

        if self.job != "apply":
            job["matrix_name"] = self.matrices.at[self.cob_seed_mat.currentIndex(), "name"]
            job["matrix_core"] = self.cob_seed_field.currentText()

        if self.job != "calibrate":
            vectors = self.datasets[self.cob_data.currentText()].copy()
            if not self._has_idx:
                vectors = vectors.set_index(self.cob_index.currentText())
            vectors.index.name = self.cob_index.currentText() if not self._has_idx else vectors.index.name
            job["vectors"] = vectors.reset_index()
            job["index_field"] = vectors.index.name
            job["row_field"] = self.cob_prod_field.currentText()
            job["column_field"] = self.cob_atra_field.currentText()

        if self.job == "calibrate":
            self.out_name = self.browse_outfile("mod")
            if self.out_name is not None:
                job["function"] = self._selected_function()
        else:
            self.out_name = self.browse_outfile("omx")
            if self.job == "apply" and self.out_name is not None:
                for i in range(1, self.table_model.rowCount()):
                    if str(self.table_model.item(i, 0).text()) == "Alpha":
                        self.model.alpha = float(self.table_model.cellWidget(i, 1).value())
                    if str(self.table_model.item(i, 0).text()) == "Beta":
                        self.model.beta = float(self.table_model.cellWidget(i, 1).value())
                job["function"] = self.model.function
                job["alpha"] = self.model.alpha
                job["beta"] = self.model.beta

        if self.out_name is None:
            return

        job["output"] = self.out_name
        self.chb_empty_as_zero.setEnabled(False)
        self.add_job_to_list(job, self.out_name)

    def _selected_function(self) -> str:
        if self.rdo_expo.isChecked():
            return "EXPO"
        if self.rdo_power.isChecked():
            return "POWER"
        if self.rdo_gamma.isChecked():
            return "GAMMA"
        return "FRICTION"

    def add_job_to_list(self, job, out_name):
        self.job_queue[out_name] = job

        self.table_jobs.clearContents()
        self.table_jobs.setRowCount(len(self.job_queue.keys()))

        for i, j in enumerate(self.job_queue.keys()):
            data_name = splitext(basename(j))[0]
            self.table_jobs.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table_jobs.setItem(i, 1, QTableWidgetItem(data_name))
            self.table_jobs.setItem(i, 2, QTableWidgetItem(self.tr("Queued")))

    def run(self):
        """Run queued Processing algorithms without blocking the QGIS interface."""
        self.chb_empty_as_zero.setVisible(False)
        self.but_run.setEnabled(False)
        self.but_queue.setEnabled(False)
        self._pending_jobs = list(self.job_queue.items())
        self.report = []
        self._run_next_job()

    def _run_next_job(self):
        if not self._pending_jobs:
            self.but_run.setEnabled(True)
            self.but_queue.setEnabled(True)
            self.exit_procedure()
            return

        out_name, job = self._pending_jobs.pop(0)
        self.outfile = out_name
        try:
            algorithm_id, parameters = self._algorithm_parameters(job)
            registry = QgsApplication.processingRegistry()
            algorithm = registry.algorithmById(algorithm_id)
            if algorithm is None:
                from qaequilibrae.modules.processing_provider.distribution_procedures.apply_gravity import ApplyGravity
                from qaequilibrae.modules.processing_provider.distribution_procedures.calibrate_gravity import (
                    CalibrateGravity,
                )
                from qaequilibrae.modules.processing_provider.distribution_procedures.iterative_proportional_fitting import (
                    IterativeProportionalFitting,
                )

                algorithms = {
                    "qaequilibrae:apply_gravity_model": ApplyGravity,
                    "qaequilibrae:calibrate_gravity_model": CalibrateGravity,
                    "qaequilibrae:iterative_proportional_fitting": IterativeProportionalFitting,
                }
                algorithm_class = algorithms.get(algorithm_id)
                if algorithm_class is None:
                    raise RuntimeError(f"Processing algorithm '{algorithm_id}' is not available")
                algorithm = algorithm_class()
                algorithm.initAlgorithm()

            self._task_context = QgsProcessingContext()
            self._task_context.setProject(QgsProject.instance())
            self._task_feedback = QgsProcessingFeedback()
            self._task = QgsProcessingAlgRunnerTask(algorithm, parameters, self._task_context, self._task_feedback)
            self._task.executed.connect(self._algorithm_finished)
            QgsApplication.taskManager().addTask(self._task)
        except Exception as error:
            self._task_failed(str(error))

    def _algorithm_parameters(self, job: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Build Processing parameters for a queued job."""
        base = {"PROJECT_FOLDER": str(self.project.project_base_path), "NAN_AS_ZERO": job["nan_as_zero"]}
        if job["kind"] != "calibrate":
            self._task_layer = layer_from_dataframe(job["vectors"], "distribution_vectors")
            base.update(
                {
                    "VECTOR_SOURCE": self._task_layer,
                    "INDEX_FIELD": job["index_field"],
                    "ROW_FIELD": job["row_field"],
                    "COLUMN_FIELD": job["column_field"],
                }
            )
        if job["kind"] == "ipf":
            base.update(
                {
                    "SEED_MATRIX_NAME": job["matrix_name"],
                    "SEED_MATRIX_CORE": job["matrix_core"],
                    "OUTPUT_MATRIX": job["output"],
                }
            )
            return "qaequilibrae:iterative_proportional_fitting", base
        if job["kind"] == "apply":
            base.update(
                {
                    "IMPEDANCE_MATRIX_NAME": job["impedance_name"],
                    "IMPEDANCE_MATRIX_CORE": job["impedance_core"],
                    "FUNCTION": ["EXPO", "GAMMA", "POWER"].index(job["function"]),
                    "ALPHA": job["alpha"],
                    "BETA": job["beta"],
                    "OUTPUT_MATRIX": job["output"],
                }
            )
            return "qaequilibrae:apply_gravity_model", base
        base.update(
            {
                "OBSERVED_MATRIX_NAME": job["matrix_name"],
                "OBSERVED_MATRIX_CORE": job["matrix_core"],
                "IMPEDANCE_MATRIX_NAME": job["impedance_name"],
                "IMPEDANCE_MATRIX_CORE": job["impedance_core"],
                "FUNCTION": ["EXPO", "POWER"].index(job["function"]),
                "OUTPUT_MODEL": job["output"],
            }
        )
        return "qaequilibrae:calibrate_gravity_model", base

    def _algorithm_finished(self, successful, results):
        layer = self._task_layer
        if layer is not None:
            QgsProject.instance().removeMapLayer(layer.id())
            self._task_layer = None
        if not successful:
            message = self._task_feedback.textLog() if self._task_feedback is not None else ""
            self._task = None
            self._task_failed(message or "Distribution algorithm failed")
            return
        log = self._task_feedback.textLog() if self._task_feedback is not None else ""
        if log:
            self.report.extend(line for line in log.splitlines() if line.strip())
        self._task = self._task_context = self._task_feedback = None
        self._run_next_job()

    def _task_failed(self, message: str):
        logger.error("Distribution Processing task failed: %s", message)
        if self._task_layer is not None:
            QgsProject.instance().removeMapLayer(self._task_layer.id())
            self._task_layer = None
        self._pending_jobs.clear()
        self.but_run.setEnabled(True)
        self.but_queue.setEnabled(True)
        self._task = self._task_context = self._task_feedback = None
        self.qgis_project.iface_error_message(message, self.tr("Procedure error:"))

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

    def exit_procedure(self):
        if self.report is not None:
            dlg2 = ReportDialog(qgis.utils.iface.mainWindow(), self.report)
            dlg2.show()
            dlg2.exec()

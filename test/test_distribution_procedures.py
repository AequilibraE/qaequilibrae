from os.path import basename, isfile, splitext

import numpy as np
import openmatrix as omx
import pandas as pd
import pytest
from aequilibrae.matrix import AequilibraeMatrix
from PyQt5.QtCore import Qt
from qgis.core import QgsProject

from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe
from qaequilibrae.modules.distribution_procedures.distribution_models_dialog import DistributionModelsDialog
from qaequilibrae.modules.matrix_procedures.load_dataset_dialog import LoadDatasetDialog
from .utilities import run_sfalls_assignment

DISTRIBUTION_PATH = "qaequilibrae.modules.distribution_procedures.distribution_models_dialog.DistributionModelsDialog"


@pytest.mark.parametrize("method", ["csv", "parquet", "open layer"])
def test_ipf(ae_with_project, folder_path, mocker, method):

    df = pd.read_csv("test/data/SiouxFalls_project/synthetic_future_vector.csv")
    _ = layer_from_dataframe(df, "synthetic_future_vector")

    file_path = f"{folder_path}/demand_ipf_D.aem"
    mocked_outfile = mocker.patch(f"{DISTRIBUTION_PATH}.browse_outfile")
    mocked_outfile.return_value = file_path

    dialog = DistributionModelsDialog(ae_with_project, mode="ipf")

    if method == "csv":
        dataset_path = "test/data/SiouxFalls_project/synthetic_future_vector.csv"
        dataset = pd.read_csv(dataset_path)
    elif method == "parquet":
        dataset_path = "test/data/SiouxFalls_project/synthetic_future_vector.parquet"
        dataset = pd.read_parquet(dataset_path)
    elif method == "open layer":
        layer = QgsProject.instance().mapLayersByName("synthetic_future_vector")[0]
        dialog.iface.setActiveLayer(layer)

    if method in ["csv", "parquet"]:
        data_name = splitext(basename(dataset_path))[0]
        dialog.datasets[data_name] = dataset

        dialog.cob_index.setCurrentText("index")
        dialog._has_idx = False
    else:
        dataset = LoadDatasetDialog(dialog.qgis_project)
        dataset.radio_layer.setChecked(True)
        dataset.size_it_accordingly(True)
        dataset.cob_index_field.setCurrentText("index")
        dataset.layer = layer
        dataset.load_the_vector()

        dialog.datasets["synthetic_future_vector"] = dataset.dataset
        dialog._has_idx = True
        dialog.cob_index.clear()
        dialog.cob_index.setEnabled(False)

    dialog.outfile = file_path
    dialog.load_comboboxes(dialog.datasets.keys(), dialog.cob_data)

    temp = list(dialog.matrices["name"])
    demand_idx = temp.index("demand.aem")
    dialog.cob_seed_mat.setCurrentIndex(demand_idx)
    dialog.cob_seed_field.setCurrentText("matrix")

    dialog.cob_prod_field.setCurrentText("origins")
    dialog.cob_atra_field.setCurrentText("destinations")

    dialog.add_job_to_queue()
    dialog.worker_thread = dialog.job_queue[dialog.outfile]
    dialog.worker_thread.doWork()

    dialog.worker_thread.output.export(dialog.outfile)

    assert isfile(file_path)

    mat = AequilibraeMatrix()
    mat.load(file_path)
    assert mat.matrix["matrix"].shape == (24, 24)
    assert np.sum(np.nan_to_num(mat.matrix["matrix"])[:, :]) > 360600


@pytest.mark.parametrize("method", ["negative_exponential", "inverse_power", "both"])
def test_calibrate_gravity(sf_project, method, folder_path, mocker, qtbot):
    proj = run_sfalls_assignment(sf_project)

    mocked_outfile = mocker.patch(f"{DISTRIBUTION_PATH}.browse_outfile")
    mocker.patch(f"{DISTRIBUTION_PATH}.exit_procedure")

    dialog = DistributionModelsDialog(proj, mode="calibrate")

    temp = list(dialog.matrices["name"])
    imped_idx = temp.index("assignment_car")
    demand_idx = temp.index("demand_omx")
    dialog.cob_imped_mat.setCurrentIndex(imped_idx)
    dialog.cob_imped_field.setCurrentText("free_flow_time_final")
    dialog.cob_seed_mat.setCurrentIndex(demand_idx)
    dialog.cob_seed_field.setCurrentText("matrix")

    if method in ["negative_exponential", "both"]:
        mocked_outfile.return_value = f"{folder_path}/neg_{method}.mod"
        dialog.rdo_expo.setChecked(True)
        qtbot.mouseClick(dialog.but_queue, Qt.LeftButton)

    if method in ["inverse_power", "both"]:
        mocked_outfile.return_value = f"{folder_path}/inv_{method}.mod"
        dialog.rdo_power.setChecked(True)
        qtbot.mouseClick(dialog.but_queue, Qt.LeftButton)

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    if method in ["negative_exponential", "both"]:
        file_path = f"{folder_path}/neg_{method}.mod"
        assert isfile(file_path)

        file_text = ""
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file.readlines():
                file_text += line

        assert "alpha: null" in file_text
        assert "function: EXPO" in file_text

    if method in ["inverse_power", "both"]:
        file_path = f"{folder_path}/inv_{method}.mod"
        assert isfile(file_path)

        file_text = ""
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file.readlines():
                file_text += line

        assert "beta: null" in file_text
        assert "function: POWER" in file_text


@pytest.mark.parametrize("method", ["negative", "power", "gamma"])
def test_apply_gravity(ae_with_project, method, folder_path, mocker):

    file_path = f"{folder_path}/matrices/ADJ-TrafficAssignment_DP.omx"
    mocked_outfile = mocker.patch(f"{DISTRIBUTION_PATH}.browse_outfile")
    mocked_outfile.return_value = file_path

    dataset_path = "test/data/SiouxFalls_project/synthetic_future_vector.csv"
    dataset = pd.read_csv(dataset_path)

    data_name = splitext(basename(dataset_path))[0]

    dialog = DistributionModelsDialog(ae_with_project, mode="apply")
    dialog._has_idx = False

    dialog.datasets[data_name] = dataset
    dialog.load_comboboxes(dialog.datasets.keys(), dialog.cob_data)

    temp = list(dialog.matrices["name"])
    imped_idx = temp.index("trafficassignment_dp_x_car_omx")
    dialog.cob_imped_mat.setCurrentIndex(imped_idx)
    dialog.cob_imped_field.setCurrentText("free_flow_time_final")

    dialog.cob_data.setCurrentText("synthetic_future_vector")
    dialog.cob_index.setCurrentText("index")
    dialog.cob_prod_field.setCurrentText("origins")
    dialog.cob_atra_field.setCurrentText("destinations")

    if method == "negative":
        model_file = "test/data/SiouxFalls_project/mod_negative_exponential_X.mod"
        dialog.model.load(model_file)
        dialog.update_model_parameters()
    elif method == "power":
        dialog.model.function = "POWER"
        dialog.model.alpha = 0.02718039228535631
        dialog.update_model_parameters()
    else:
        dialog.model.alpha = 0.02718039228535631
        dialog.model.beta = 0.020709580776383137

    dialog.outfile = file_path

    dialog.add_job_to_queue()
    dialog.worker_thread = dialog.job_queue[dialog.outfile]
    dialog.worker_thread.doWork()
    dialog.worker_thread.output.export(dialog.outfile)

    assert isfile(file_path)

    with omx.open_file(file_path, "a") as omx_file:
        mtx = omx_file["gravity"][:]
        assert mtx.shape == (24, 24)  # matrix shape
        assert mtx.sum() > 0  # matrix is not null

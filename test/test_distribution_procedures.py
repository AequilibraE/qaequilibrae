from os.path import isfile, splitext, basename, join
from shutil import copy
import numpy as np
import openmatrix as omx
import pytest
from PyQt5.QtCore import Qt, QVariant
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from aequilibrae.matrix import AequilibraeData, AequilibraeMatrix

from qaequilibrae.modules.distribution_procedures.distribution_models_dialog import DistributionModelsDialog
from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog


def run_traffic_assignment(ae_with_project, qtbot, ext):
    dialog = TrafficAssignmentDialog(ae_with_project)

    assignment_result = f"TrafficAssignment_DP_{ext}"
    dialog.output_scenario_name.setText(assignment_result)
    dialog.cob_matrices.setCurrentText("demand.aem")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    dialog.cob_vdf.setCurrentText("BPR")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("500")
    dialog.rel_gap.setText("0.001")
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")

    dialog.run()


def load_external_vector():
    import csv

    path_to_csv = "test/data/SiouxFalls_project/synthetic_future_vector.csv"

    datalayer = QgsVectorLayer("None?delimiter=,", "synthetic_future_vector", "memory")

    fields = [
        QgsField("index", QVariant.Int),
        QgsField("origins", QVariant.Double),
        QgsField("destinations", QVariant.Double),
    ]
    datalayer.dataProvider().addAttributes(fields)
    datalayer.updateFields()

    with open(path_to_csv, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            origin = float(row["origins"])
            destination = float(row["destinations"])
            index = int(row["index"])

            feature = QgsFeature()
            feature.setAttributes([index, origin, destination])

            datalayer.dataProvider().addFeature(feature)

    if not datalayer.isValid():
        print("Open layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(datalayer)


@pytest.mark.parametrize("method", ("dataset", "open_layer"))
def test_ipf(ae_with_project, folder_path, mocker, method):

    file_path = f"{folder_path}/demand_ipf_D.aem"
    mocker.patch(
        "qaequilibrae.modules.distribution_procedures.distribution_models_dialog.DistributionModelsDialog.browse_outfile",
        return_value=file_path,
    )

    dialog = DistributionModelsDialog(ae_with_project, mode="ipf")

    if method == "dataset":
        dataset_path = "test/data/SiouxFalls_project/synthetic_future_vector.aed"
        dataset = AequilibraeData()
        dataset.load(dataset_path)

        data_name = splitext(basename(dataset_path))[0]

        dialog.datasets[data_name] = dataset
    else:
        load_external_vector()
        layer = QgsProject.instance().mapLayersByName("synthetic_future_vector")[0]
        dialog.iface.setActiveLayer(layer)
        idx = []
        origin = []
        destination = []
        for feat in layer.getFeatures():
            f = feat.attributes()
            idx.append(f[0])
            origin.append(f[1])
            destination.append(f[2])
        args = {
            "entries": 24,
            "field_names": ["origins", "destinations"],
            "data_types": [np.float64, np.float64],
            "file_path": f"{folder_path}/synthetic_future_vector_CSV.aed",
        }

        dataset = AequilibraeData()
        dataset.create_empty(**args)

        dataset.origins[:] = origin[:]
        dataset.destinations[:] = destination[:]
        dataset.index[:] = idx[:]

        dialog.datasets["synthetic_future_vector_CSV"] = dataset

    dialog.outfile = file_path

    dialog.load_comboboxes(dialog.datasets.keys(), dialog.cob_prod_data)
    dialog.load_comboboxes(dialog.datasets.keys(), dialog.cob_atra_data)

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


@pytest.mark.parametrize(("method", "ext"), [("negative_exponential", "A"), ("inverse_power", "B"), ("both", "C")])
def test_calibrate_gravity(ae_with_project, qtbot, method, ext, folder_path, mocker):
    run_traffic_assignment(ae_with_project, qtbot, ext)

    file_path = f"{folder_path}/mod_{method}_{ext}.mod"
    mocker.patch(
        "qaequilibrae.modules.distribution_procedures.distribution_models_dialog.DistributionModelsDialog.browse_outfile",
        return_value=file_path,
    )

    dialog = DistributionModelsDialog(ae_with_project, mode="calibrate")

    temp = list(dialog.matrices["name"])
    imped_idx = temp.index(f"TrafficAssignment_DP_{ext}_car")
    demand_idx = temp.index("omx")
    dialog.cob_imped_mat.setCurrentIndex(imped_idx)
    dialog.cob_imped_field.setCurrentText("free_flow_time_final")
    dialog.cob_seed_mat.setCurrentIndex(demand_idx)
    dialog.cob_seed_field.setCurrentText("matrix")

    if method == "negative_exponential":
        dialog.rdo_expo.setChecked(True)
    elif method == "inverse_power":
        dialog.rdo_power.setChecked(True)
    else:
        dialog.rdo_expo.setChecked(True)
        dialog.rdo_power.setChecked(True)

    dialog.outfile = file_path

    dialog.add_job_to_queue()
    dialog.worker_thread = dialog.job_queue[dialog.outfile]
    dialog.worker_thread.doWork()
    dialog.worker_thread.model.save(dialog.outfile)

    assert isfile(file_path)

    if method in ["negative_exponential"]:
        file_text = ""
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file.readlines():
                file_text += line

        assert "alpha: null" in file_text
        assert "function: EXPO" in file_text

    elif method in ["inverse_power", "both"]:
        file_text = ""
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file.readlines():
                file_text += line

        assert "beta: null" in file_text
        assert "function: POWER" in file_text


@pytest.mark.parametrize(("method", "ext"), [("negative", "X"), ("power", "Y"), ("gamma", "Z")])
def test_apply_gravity(ae_with_project, method, ext, folder_path, mocker):

    file_path = f"{folder_path}/matrices/ADJ-TrafficAssignment_DP_{ext}.omx"
    mocker.patch(
        "qaequilibrae.modules.distribution_procedures.distribution_models_dialog.DistributionModelsDialog.browse_outfile",
        return_value=file_path,
    )

    dataset_name = "test/data/SiouxFalls_project/synthetic_future_vector.aed"

    dataset = AequilibraeData()
    dataset.load(dataset_name)

    data_name = splitext(basename(dataset_name))[0]

    dialog = DistributionModelsDialog(ae_with_project, mode="apply")

    dialog.datasets[data_name] = dataset
    dialog.load_comboboxes(dialog.datasets.keys(), dialog.cob_prod_data)
    dialog.load_comboboxes(dialog.datasets.keys(), dialog.cob_atra_data)

    temp = list(dialog.matrices["name"])
    imped_idx = temp.index(f"trafficassignment_dp_x_car_omx")
    dialog.cob_imped_mat.setCurrentIndex(imped_idx)
    dialog.cob_imped_field.setCurrentText("free_flow_time_final")

    dialog.cob_prod_data.setCurrentText("synthetic_future_vector")
    dialog.cob_prod_field.setCurrentText("origins")
    dialog.cob_atra_data.setCurrentText("synthetic_future_vector")
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

    mtx = omx.open_file(file_path)
    mtx = mtx["gravity"][:]
    assert mtx.shape == (24, 24)  # matrix shape
    assert mtx.sum() > 0  # matrix is not null

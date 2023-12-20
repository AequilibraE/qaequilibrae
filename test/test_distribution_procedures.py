from os.path import isfile, splitext, basename

import numpy as np
import openmatrix as omx
import pytest
from PyQt5.QtCore import Qt, QVariant
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from aequilibrae.matrix import AequilibraeData, AequilibraeMatrix

from qaequilibrae.modules.distribution_procedures.distribution_models_dialog import DistributionModelsDialog
from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog
from qaequilibrae.modules.matrix_procedures.load_dataset_dialog import LoadDatasetDialog


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


@pytest.mark.parametrize(("is_dataset", "is_layer"), [(True, False), (False, True)])
def test_ipf(ae_with_project, qtbot, is_dataset, is_layer):
    dialog = DistributionModelsDialog(ae_with_project, mode="ipf", testing=True)

    if is_dataset:
        dataset_name = "test/data/SiouxFalls_project/synthetic_future_vector.aed"
        dataset = AequilibraeData()
        dataset.load(dataset_name)

        data_name = splitext(basename(dataset_name))[0]

        file_path = "test/data/SiouxFalls_project/demand_ipf_D.aem"
        dialog.out_name = file_path
        dialog.outfile = file_path
        dialog.datasets[data_name] = dataset

    if is_layer:
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
            "file_path": "synthetic_future_vector_CSV.aed",
        }

        dataset = AequilibraeData()
        dataset.create_empty(**args)

        dataset.origins[:] = origin[:]
        dataset.destinations[:] = destination[:]
        dataset.index[:] = idx[:]

        file_path = "test/data/SiouxFalls_project/demand_ipf_L.aem"
        dialog.out_name = file_path
        dialog.outfile = file_path
        dialog.datasets["synthetic_future_vector_CSV"] = dataset

    dialog.load_comboboxes(dialog.datasets.keys(), dialog.cob_prod_data)
    dialog.load_comboboxes(dialog.datasets.keys(), dialog.cob_atra_data)

    temp = list(dialog.matrices["name"])
    demand_idx = temp.index("demand.aem")
    dialog.cob_seed_mat.setCurrentIndex(demand_idx)
    dialog.cob_seed_field.setCurrentText("matrix")

    dialog.cob_prod_field.setCurrentText("origins")
    dialog.cob_atra_field.setCurrentText("destinations")

    qtbot.mouseClick(dialog.but_queue, Qt.LeftButton)
    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    dialog.close()

    assert isfile(file_path)

    mat = AequilibraeMatrix()
    mat.load(file_path)

    assert mat.matrix["matrix"].shape == (24, 24)
    assert np.sum(np.nan_to_num(mat.matrix["matrix"])[:, :]) > 360600


@pytest.mark.parametrize(
    ("is_negative", "is_power", "file1", "file2", "ext"),
    [
        (True, False, "mod_negative_exponential", "", "A"),
        (False, True, "", "mod_inverse_power", "B"),
        (True, True, "mod_negative_exponential", "mod_inverse_power", "C"),
    ],
)
def test_calibrate_gravity(ae_with_project, qtbot, is_negative, is_power, file1, file2, ext):
    run_traffic_assignment(ae_with_project, qtbot, ext)

    dialog = DistributionModelsDialog(ae_with_project, mode="calibrate", testing=True)

    dialog.path = "test/data/SiouxFalls_project/"

    temp = list(dialog.matrices["name"])
    imped_idx = temp.index(f"TrafficAssignment_DP_{ext}_car")
    demand_idx = temp.index("omx")
    dialog.cob_imped_mat.setCurrentIndex(imped_idx)
    dialog.cob_imped_field.setCurrentText("free_flow_time_final")
    dialog.cob_seed_mat.setCurrentIndex(demand_idx)
    dialog.cob_seed_field.setCurrentText("matrix")

    if is_negative:
        f1 = f"test/data/SiouxFalls_project/{file1}_{ext}.mod"

        dialog.out_name = f1

        dialog.rdo_expo.setChecked(True)

        qtbot.mouseClick(dialog.but_queue, Qt.LeftButton)

    if is_power:
        f2 = f"test/data/SiouxFalls_project/{file2}_{ext}.mod"

        dialog.out_name = f2

        dialog.rdo_power.setChecked(True)

        qtbot.mouseClick(dialog.but_queue, Qt.LeftButton)

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    dialog.close()

    if is_negative:
        assert isfile(f1)

        file_text = ""
        with open(f1, "r", encoding="utf-8") as file:
            for line in file.readlines():
                file_text += line

        assert "alpha: null" in file_text
        assert "function: EXPO" in file_text

    if is_power:
        assert isfile(f2)

        file_text = ""
        with open(f2, "r", encoding="utf-8") as file:
            for line in file.readlines():
                file_text += line

        assert "beta: null" in file_text
        assert "function: POWER" in file_text


@pytest.mark.parametrize(
    ("is_negative", "is_power", "is_gamma", "ext"),
    [(True, False, False, "X"), (False, True, False, "Y"), (False, False, True, "Z")],
)
def test_apply_gravity(ae_with_project, qtbot, is_negative, is_power, is_gamma, ext):
    dataset_name = "test/data/SiouxFalls_project/synthetic_future_vector.aed"
    dataset = AequilibraeData()
    dataset.load(dataset_name)

    data_name = splitext(basename(dataset_name))[0]

    dialog = DistributionModelsDialog(ae_with_project, mode="apply", testing=True)

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

    if is_negative:
        dialog.model.load(f"test/data/SiouxFalls_project/mod_negative_exponential_X.mod")
        dialog.update_model_parameters()
    elif is_power:
        dialog.model.function = "POWER"
        dialog.model.alpha = 0.02718039228535631
        dialog.update_model_parameters()
    elif is_gamma:
        dialog.model.alpha = 0.02718039228535631
        dialog.model.beta = 0.020709580776383137

    file_path = f"test/data/SiouxFalls_project/matrices/ADJ-TrafficAssignment_DP_{ext}.omx"
    dialog.out_name = file_path

    qtbot.mouseClick(dialog.but_queue, Qt.LeftButton)
    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    dialog.close()

    assert isfile(file_path)

    mtx = omx.open_file(file_path)
    mtx = mtx["gravity"][:]
    assert mtx.shape == (24, 24)  # matrix shape
    assert mtx.sum() > 0  # matrix is not null

from os.path import isfile
from uuid import uuid4

import numpy as np
import openmatrix as omx
import pandas as pd
import pytest
import yaml
from qgis.PyQt.QtCore import Qt

from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog


def test_nan_demand_is_replaced_with_zero(sf_project, qtbot, mocker):
    matrix_path = sf_project.project.project_base_path / "matrices" / "demand.omx"
    with omx.open_file(matrix_path, "a") as omx_file:
        omx_file["matrix"][0, 1] = np.nan

    dialog = TrafficAssignmentDialog(sf_project)
    dialog.cob_matrices.setCurrentText("demand_omx")
    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    warning = mocker.patch("qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.logger.warning")

    dialog._create_traffic_class()

    assert dialog.traffic_classes["car"].matrix.matrix_view[0, 1] == 0.0
    warning.assert_called_once_with("Replaced 1 NaN demand value with zero in matrix 'demand_omx' (core(s): matrix).")
    with omx.open_file(matrix_path, "r") as omx_file:
        assert np.isnan(omx_file["matrix"][0, 1])
    dialog.close()


def test_single_class(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value=f"{sf_project.project.project_base_path}/assignment_config.yml",
    )

    dialog = TrafficAssignmentDialog(sf_project)

    test_name = f"TestTrafficAssignment_SC_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)

    dialog.cob_vdf.setCurrentText("bpr")
    dialog.tbl_vdf_parameters.cellWidget(0, 2).setCurrentText("b")
    dialog.tbl_vdf_parameters.cellWidget(1, 2).setCurrentText("power")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("25")
    dialog.rel_gap.setText("0.001")

    qtbot.mouseClick(dialog.but_save_yaml, Qt.MouseButton.LeftButton)  # Save configs in YAML

    dialog.run()

    with pytest.raises(ValueError):
        dialog.produce_all_outputs()

    dialog.close()

    results = sf_project.project._results_database_path
    assert isfile(results)

    # Assert we have a non-null result and that results are actually stored in the file
    with sf_project.project.results_connection as conn:
        assert conn.execute(f"SELECT ROUND(SUM(PCE_tot), 4) FROM {test_name}").fetchone()[0] > 0

    pth = sf_project.project.project_base_path
    skims = pth / "matrices" / f"{test_name}_car.omx"
    assert isfile(skims)

    with omx.open_file(skims, "a") as omx_file:
        assert round(np.sum(np.nan_to_num(omx_file["free_flow_time_final"][:])), 4) > 0
        assert round(np.sum(np.nan_to_num(omx_file["free_flow_time_blended"][:])), 4) > 0
        assert round(np.sum(np.nan_to_num(omx_file["distance_final"][:])), 4) > 0
        assert round(np.sum(np.nan_to_num(omx_file["distance_blended"][:])), 4) > 0

    # Check if YAML was saved
    assert isfile(pth / "assignment_config.yml")


def test_multiclass(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value=f"{sf_project.project.project_base_path}/mc_config.yml",
    )

    dialog = TrafficAssignmentDialog(sf_project)

    test_name = f"TestTrafficAssignment_MC_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand_mc")

    # Traffic class - Car
    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    # Adds car skims
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    dialog.cob_skim_class.setCurrentText("car")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    dialog.cob_skim_class.setCurrentText("car")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)

    # Traffic Class Trucks
    dialog.tbl_core_list.selectRow(2)
    dialog.cob_mode_for_class.setCurrentIndex(4)
    dialog.ln_class_name.setText("trucks")
    dialog.pce_setter.setValue(2.5)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    # Adds truck skims
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    dialog.cob_skim_class.setCurrentText("trucks")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    dialog.cob_skim_class.setCurrentText("trucks")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)

    # Traffic Class Motorcycle
    dialog.tbl_core_list.selectRow(1)
    dialog.cob_mode_for_class.setCurrentIndex(5)
    dialog.cob_mode_for_class.setCurrentText("motorcycle")
    dialog.pce_setter.setValue(0.2)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    # Adds motorcycle skims
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    dialog.cob_skim_class.setCurrentText("motorcycles")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    dialog.cob_skim_class.setCurrentText("motorcycles")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)

    # Assignment setup
    dialog.cob_vdf.setCurrentText("bpr")
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("20")
    dialog.rel_gap.setText("0.001")

    qtbot.mouseClick(dialog.but_save_yaml, Qt.MouseButton.LeftButton)  # Save configs in YAML

    dialog.run()

    with pytest.raises(ValueError):
        dialog.produce_all_outputs()

    dialog.close()

    # Assert we have a non-null result and that results are actually stored in the file
    results = sf_project.project._results_database_path
    assert isfile(results)

    with sf_project.project.results_connection as conn:
        assert conn.execute(f"SELECT ROUND(SUM(PCE_tot), 4) FROM {test_name}").fetchone()[0] > 0
        assert conn.execute(f"SELECT ROUND(SUM(car_tot), 4) FROM {test_name}").fetchone()[0] > 0
        assert conn.execute(f"SELECT ROUND(SUM(motorcycle_tot), 4) FROM {test_name}").fetchone()[0] > 0
        assert conn.execute(f"SELECT ROUND(SUM(trucks_tot), 4) FROM {test_name}").fetchone()[0] > 0

    pth = dialog.project.project_base_path
    assert isfile(pth / "matrices" / f"{test_name}_car.omx")
    assert isfile(pth / "matrices" / f"{test_name}_motorcycles.omx")
    assert isfile(pth / "matrices" / f"{test_name}_trucks.omx")

    # Check if YAML was saved
    assert isfile(sf_project.project.project_base_path / "mc_config.yml")


def test_all_or_nothing(sf_project, qtbot):
    dialog = TrafficAssignmentDialog(sf_project)

    test_name = f"TestTrafficAssignment_AON_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)

    dialog.cob_vdf.setCurrentText("bpr")
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("all-or-nothing")

    dialog.run()

    with pytest.raises(ValueError):
        dialog.produce_all_outputs()

    dialog.close()

    results = sf_project.project._results_database_path
    assert isfile(results)

    # Assert we have a non-null result and that results are actually stored in the file
    with sf_project.project.results_connection as conn:
        assert conn.execute(f"SELECT ROUND(SUM(matrix_tot), 4) FROM {test_name}").fetchone()[0] == 885_300.0

    pth = dialog.project.project_base_path
    skims = pth / "matrices" / f"{test_name}_car.omx"
    assert isfile(skims)


def test_select_link_analysis(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value=f"{sf_project.project.project_base_path}/sl_config.yml",
    )
    dialog = TrafficAssignmentDialog(sf_project)

    test_name = f"TestTrafficAssignment_SLA_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand_omx")

    # Traffic classes
    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)

    # Select link
    dialog.do_select_link.setChecked(True)
    dialog.input_qry_name.setText("Leaving from 1")
    dialog.input_link_id.setText("1")
    qtbot.mouseClick(dialog.but_add_query, Qt.MouseButton.LeftButton)
    dialog.input_link_id.setText("2")
    qtbot.mouseClick(dialog.but_add_query, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.but_build_query, Qt.MouseButton.LeftButton)
    dialog.sl_mat_name.setText("select_link_analysis")

    # Assignment
    dialog.cob_vdf.setCurrentText("bpr")
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("25")
    dialog.rel_gap.setText("0.001")

    qtbot.mouseClick(dialog.but_save_yaml, Qt.MouseButton.LeftButton)  # Save configs in YAML

    dialog.run()

    matrices = dialog.project.matrices
    matrices.update_database()
    assert "select_link_analysis.omx" in matrices.list()["file_name"].tolist()

    with dialog.project.results_connection as conn:
        results = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    assert "select_link_analysis" in results

    # Check if YAML was saved
    assert isfile(sf_project.project.project_base_path / "sl_config.yml")


def test_link_removal(sf_project, qtbot):
    links = [9, 10, 11, 13, 23, 25, 26, 27, 28, 31, 32, 34, 40, 41, 43, 44]
    layer = sf_project.layers["links"][0]
    layer.select([f.id() for f in layer.getFeatures() if f["link_id"] in links])

    dialog = TrafficAssignmentDialog(sf_project)

    test_name = "TestTrafficAssignment_LinkRemoval"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand_omx")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    dialog.chb_chosen_links.setChecked(True)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)

    dialog.cob_vdf.setCurrentText("bpr")
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("25")
    dialog.rel_gap.setText("0.001")

    dialog.run()

    with pytest.raises(ValueError):
        dialog.produce_all_outputs()

    dialog.close()

    project = sf_project.project
    matrices = project.matrices
    matrices.update_database()
    assert f"{test_name}_car" in matrices.list()["name"].values.tolist()

    with project.results_connection as conn:
        results = pd.read_sql(f"Select link_id, PCE_tot from {test_name}", conn).set_index("link_id")

    for idx, row in results.iterrows():
        if idx in links:
            assert row["PCE_tot"] == 0
        else:
            assert row["PCE_tot"] > 0


def test_single_class_from_yaml(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value="test/data/SiouxFalls_project/assignment_config.yml",
    )

    dialog = TrafficAssignmentDialog(sf_project)
    qtbot.mouseClick(dialog.but_load_yaml, Qt.MouseButton.LeftButton)

    dialog.run()
    dialog.close()

    assert isfile(sf_project.project._results_database_path)

    # Assert we have a non-null result and that results are actually stored in the file
    with sf_project.project.results_connection as conn:
        assert conn.execute("SELECT ROUND(SUM(PCE_tot), 4) FROM result_test_from_yaml").fetchone()[0] > 0

    pth = sf_project.project.project_base_path
    skims = pth / "matrices" / "result_test_from_yaml_car.omx"
    assert isfile(skims)

    mtx = omx.open_file(skims)
    assert round(np.sum(np.nan_to_num(mtx["free_flow_time_final"][:])), 4) > 0
    assert round(np.sum(np.nan_to_num(mtx["free_flow_time_blended"][:])), 4) > 0
    assert round(np.sum(np.nan_to_num(mtx["distance_final"][:])), 4) > 0
    assert round(np.sum(np.nan_to_num(mtx["distance_blended"][:])), 4) > 0


def test_multi_class_from_yaml(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value="test/data/SiouxFalls_project/mc_config.yml",
    )

    dialog = TrafficAssignmentDialog(sf_project)
    qtbot.mouseClick(dialog.but_load_yaml, Qt.MouseButton.LeftButton)

    # The config asks for BPR2, and the combo entries are lower case
    assert dialog.cob_vdf.currentText() == "bpr2"

    dialog.run()
    dialog.close()

    # Assert we have a non-null result and that results are actually stored in the file
    assert isfile(sf_project.project._results_database_path)

    with sf_project.project.results_connection as conn:
        assert conn.execute("SELECT ROUND(SUM(PCE_tot), 4) FROM result_test_from_yaml").fetchone()[0] > 0
        assert conn.execute("SELECT ROUND(SUM(car_tot), 4) FROM result_test_from_yaml").fetchone()[0] > 0
        assert conn.execute("SELECT ROUND(SUM(motorcycle_tot), 4) FROM result_test_from_yaml").fetchone()[0] > 0

    pth = sf_project.project.project_base_path
    assert isfile(pth / "matrices" / "result_test_from_yaml_car.omx")
    assert isfile(pth / "matrices" / "result_test_from_yaml_motorcycle.omx")


def test_fixed_cost_from_yaml(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value="test/data/SiouxFalls_project/fixed_cost_config.yml",
    )

    dialog = TrafficAssignmentDialog(sf_project)
    qtbot.mouseClick(dialog.but_load_yaml, Qt.MouseButton.LeftButton)

    # The config gives a fixed cost to the car class only
    assert dialog.cob_fixed_cost.currentText() == "toll"
    assert dialog.vot_setter.value() == 2.5
    assert dialog.traffic_classes["car"].fixed_cost_field == "toll"
    assert dialog.traffic_classes["car"].vot == 2.5

    # ... so the class loaded after it must not inherit one
    assert not dialog.chb_fixed_cost.isChecked()
    assert dialog.traffic_classes["motorcycle"].fixed_cost_field == ""

    # And that distinction has to survive a round trip through the exporter
    saved_yaml = f"{sf_project.project.project_base_path}/fixed_cost_config.yml"
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value=saved_yaml,
    )
    qtbot.mouseClick(dialog.but_save_yaml, Qt.MouseButton.LeftButton)

    with open(saved_yaml, "r") as f:
        saved = yaml.safe_load(f)

    saved_classes = {name: config for tc in saved["traffic_classes"] for name, config in tc.items()}
    assert saved_classes["car"]["fixed_cost"] == "toll"
    assert saved_classes["car"]["vot"] == 2.5
    assert "fixed_cost" not in saved_classes["motorcycle"]

    dialog.run()
    dialog.close()

    assert isfile(sf_project.project._results_database_path)

    with sf_project.project.results_connection as conn:
        assert conn.execute("SELECT ROUND(SUM(PCE_tot), 4) FROM result_fixed_cost_from_yaml").fetchone()[0] > 0


def test_mixed_case_from_yaml(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value="test/data/SiouxFalls_project/mixed_case_config.yml",
    )

    dialog = TrafficAssignmentDialog(sf_project)
    qtbot.mouseClick(dialog.but_load_yaml, Qt.MouseButton.LeftButton)

    # Every option the config names in a different case still resolves to the project's own spelling
    assert dialog.cob_matrices.currentText() == "demand_omx"
    assert dialog.cob_fixed_cost.currentText() == "toll"
    assert dialog.cb_choose_algorithm.currentText() == "bfw"
    assert dialog.cob_capacity.currentText() == "capacity"
    assert dialog.cob_ffttime.currentText() == "free_flow_time"
    assert dialog.cob_vdf.currentText() == "bpr"
    assert dialog.tbl_vdf_parameters.cellWidget(0, 2).currentText() == "b"
    assert dialog.tbl_vdf_parameters.cellWidget(1, 2).currentText() == "power"

    dialog.run()
    dialog.close()

    with sf_project.project.results_connection as conn:
        assert conn.execute("SELECT ROUND(SUM(PCE_tot), 4) FROM result_mixed_case_from_yaml").fetchone()[0] > 0


@pytest.mark.parametrize(
    "section, key",
    [
        ("traffic_class", "matrix_name"),
        ("traffic_class", "fixed_cost"),
        ("assignment", "algorithm"),
        ("assignment", "capacity_field"),
        ("assignment", "time_field"),
        ("assignment", "vdf"),
        ("assignment", "alpha"),
    ],
)
def test_config_with_unavailable_option(sf_project, mocker, section, key):
    with open("test/data/SiouxFalls_project/mixed_case_config.yml", "r") as f:
        config = yaml.safe_load(f)

    target = config["traffic_classes"][0]["car"] if section == "traffic_class" else config["assignment"]
    target[key] = "not_an_option"

    config_path = f"{sf_project.project.project_base_path}/invalid_config.yml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value=config_path,
    )

    dialog = TrafficAssignmentDialog(sf_project)

    # Loaded directly instead of through the button: an exception crossing a Qt slot never makes it
    # back here, and refusing the config is the whole point of this test
    with pytest.raises(ValueError, match="'not_an_option' is not an available"):
        dialog._load_configs()

    dialog.close()


def test_select_links_from_yaml(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_yaml_path",
        return_value="test/data/SiouxFalls_project/sl_config.yml",
    )

    dialog = TrafficAssignmentDialog(sf_project)
    qtbot.mouseClick(dialog.but_load_yaml, Qt.MouseButton.LeftButton)

    dialog.run()

    matrices = dialog.project.matrices
    matrices.update_database()
    assert "select_link_analysis_from_yaml.omx" in matrices.list()["file_name"].tolist()

    with sf_project.project.results_connection as conn:
        results = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
        assert "select_link_analysis_from_yaml" in results


def _configure_single_class(dialog, qtbot):
    dialog.output_scenario_name.setText(f"TestTrafficAssignment_Stale_{uuid4().hex[:6]}")
    dialog.cob_matrices.setCurrentText("demand")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    dialog.cob_vdf.setCurrentText("bpr")
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("all-or-nothing")


def test_network_fix_is_picked_up_when_dialog_reopens(sf_project, qtbot):
    """An assignment that failed on bad link data must succeed once the data is fixed.

    Graphs are cached in the project and outlive the dialog, so a stale one used to make
    the very same assignment fail on every reopen until the project itself was closed.
    """
    project = sf_project.project

    with project.db_connection as conn:
        conn.execute("UPDATE links SET capacity_ab = NULL WHERE link_id = 1")

    dialog = TrafficAssignmentDialog(sf_project)
    _configure_single_class(dialog, qtbot)

    dialog.run()
    assert "NaN" in dialog.error
    assert dialog.worker_thread is None

    dialog.close()

    # The user fixes the network and opens the dialog again, without closing the project
    with project.db_connection as conn:
        conn.execute("UPDATE links SET capacity_ab = 1000 WHERE link_id = 1")

    dialog = TrafficAssignmentDialog(sf_project)
    _configure_single_class(dialog, qtbot)

    graph = dialog.traffic_classes["car"].graph.graph
    assert not pd.isna(graph["capacity"]).any()

    dialog.close()


def test_single_class_from_python(sf_project, qtbot, mocker):
    mocker.patch(
        "qaequilibrae.modules.paths_procedures.traffic_assignment_dialog.TrafficAssignmentDialog._browse_python_path",
        return_value=f"{sf_project.project.project_base_path}/run/traffic_assignment.py",
    )

    dialog = TrafficAssignmentDialog(sf_project)

    test_name = f"TestTrafficAssignment_SC_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.MouseButton.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.MouseButton.LeftButton)

    dialog.cob_vdf.setCurrentText("bpr")
    dialog.tbl_vdf_parameters.cellWidget(0, 2).setCurrentText("b")
    dialog.tbl_vdf_parameters.cellWidget(1, 2).setCurrentText("power")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("25")
    dialog.rel_gap.setText("0.001")

    qtbot.mouseClick(dialog.but_save_python, Qt.MouseButton.LeftButton)  # Save configs in Python file

    dialog.close()

    project = sf_project.project
    project.run.run_assignment()

    assert isfile(sf_project.project._results_database_path)

    # Assert we have a non-null result and that results are actually stored in the file
    with sf_project.project.results_connection as conn:
        assert conn.execute(f"SELECT ROUND(SUM(PCE_tot), 4) FROM {test_name}").fetchone()[0] > 0

    skims = sf_project.project.project_base_path / "matrices" / f"{test_name}_car.omx"
    assert isfile(skims)

    with omx.open_file(skims, "a") as omx_file:
        assert round(np.sum(np.nan_to_num(omx_file["free_flow_time_final"][:])), 4) > 0
        assert round(np.sum(np.nan_to_num(omx_file["free_flow_time_blended"][:])), 4) > 0
        assert round(np.sum(np.nan_to_num(omx_file["distance_final"][:])), 4) > 0
        assert round(np.sum(np.nan_to_num(omx_file["distance_blended"][:])), 4) > 0

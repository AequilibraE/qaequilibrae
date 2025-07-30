import sqlite3
from os.path import isfile, join
from pathlib import Path
from uuid import uuid4

import numpy as np
import openmatrix as omx
import pandas as pd
import pytest
from PyQt5.QtCore import Qt

from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog


def test_single_class(ae_with_project, qtbot):
    dialog = TrafficAssignmentDialog(ae_with_project)

    test_name = f"TestTrafficAssignment_SC_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand.aem")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_vdf.setCurrentText("BPR")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("25")
    dialog.rel_gap.setText("0.001")

    dialog.run()

    with pytest.raises(ValueError):
        dialog.produce_all_outputs()

    dialog.close()

    pth = Path(dialog.project.project_base_path)
    results = pth / "results_database.sqlite"
    assert isfile(results)

    # Assert we have a non-null result and that results are actually stored in the file
    con = sqlite3.connect(results)
    assert con.execute(f"SELECT ROUND(SUM(PCE_tot), 4) FROM {test_name}").fetchone()[0] > 0

    skims = pth / ("matrices/" + test_name + "_car.omx")
    assert isfile(skims)

    mtx = omx.open_file(skims)
    assert round(np.sum(np.nan_to_num(mtx["free_flow_time_final"][:])), 4) > 0
    assert round(np.sum(np.nan_to_num(mtx["free_flow_time_blended"][:])), 4) > 0
    assert round(np.sum(np.nan_to_num(mtx["distance_final"][:])), 4) > 0
    assert round(np.sum(np.nan_to_num(mtx["distance_blended"][:])), 4) > 0

    # Assert information exists in the log file
    num_cores = dialog.assignment.cores
    log_ = pth / "aequilibrae.log"
    assert isfile(log_)

    file_text = ""
    with open(log_, "r", encoding="utf-8") as file:
        for line in file.readlines():
            file_text += line

    assert "INFO ; Traffic Class specification" in file_text
    assert (
        """INFO ; {'car': {'Graph': "{'Mode': 'c', 'Block through centroids': False, 'Number of centroids': 24, 'Links': 76, 'Nodes': 24}","""
        in file_text
    )
    assert (
        """'Number of centroids': 24, 'Matrix cores': ['matrix'], 'Matrix totals': {'matrix': 360600.0}}"}}"""
        in file_text
    )
    assert "INFO ; Traffic Assignment specification" in file_text
    assert "{{'VDF parameters': {{'alpha': 0.15, 'beta': 4.0}}, 'VDF function': 'bpr', 'Number of cores': {}, 'Capacity field': 'capacity', 'Time field': 'free_flow_time', 'Algorithm': 'bfw', 'Maximum iterations': 25, 'Target RGAP': 0.001}}".format(
        num_cores
    )


def test_multiclass(ae_with_project, qtbot):
    dialog = TrafficAssignmentDialog(ae_with_project)

    test_name = f"TestTrafficAssignment_MC_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand_mc")

    # Traffic class - Car
    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Adds car skims
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    dialog.cob_skim_class.setCurrentText("car")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    dialog.cob_skim_class.setCurrentText("car")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    # Traffic Class Trucks
    dialog.tbl_core_list.selectRow(2)
    dialog.cob_mode_for_class.setCurrentIndex(4)
    dialog.ln_class_name.setText("Trucks")
    dialog.pce_setter.setValue(2.5)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Adds truck skims
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    dialog.cob_skim_class.setCurrentText("Trucks")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    dialog.cob_skim_class.setCurrentText("Trucks")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    # Traffic Class Motorcycle
    dialog.tbl_core_list.selectRow(1)
    dialog.cob_mode_for_class.setCurrentIndex(3)
    dialog.cob_mode_for_class.setCurrentText("Motorcycle")
    dialog.pce_setter.setValue(0.2)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Adds motorcycle skims
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    dialog.cob_skim_class.setCurrentText("Motorcycle")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    dialog.cob_skim_class.setCurrentText("Motorcycle")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    # Assignment setup
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_vdf.setCurrentText("BPR")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("20")
    dialog.rel_gap.setText("0.001")

    dialog.run()

    with pytest.raises(ValueError):
        dialog.produce_all_outputs()

    dialog.close()

    # Assert we have a non-null result and that results are actually stored in the file
    pth = Path(dialog.project.project_base_path)
    results = pth / "results_database.sqlite"
    assert isfile(results)

    con = sqlite3.connect(results)
    assert con.execute(f"SELECT ROUND(SUM(PCE_tot), 4) FROM {test_name}").fetchone()[0] > 0
    assert con.execute(f"SELECT ROUND(SUM(car_tot), 4) FROM {test_name}").fetchone()[0] > 0
    assert con.execute(f"SELECT ROUND(SUM(motorcycle_tot), 4) FROM {test_name}").fetchone()[0] > 0
    assert con.execute(f"SELECT ROUND(SUM(trucks_tot), 4) FROM {test_name}").fetchone()[0] > 0

    assert isfile(pth / ("matrices/" + test_name + "_car.omx"))
    assert isfile(pth / ("matrices/" + test_name + "_Motorcycle.omx"))
    assert isfile(pth / ("matrices/" + test_name + "_Trucks.omx"))

    # Assert information exists in the log file
    num_cores = dialog.assignment.cores
    log_ = pth / "aequilibrae.log"
    assert isfile(log_)

    file_text = ""
    with open(log_, "r", encoding="utf-8") as file:
        for line in file.readlines():
            file_text += line

    assert "INFO ; Traffic Class specification" in file_text
    assert (
        """INFO ; {'car': {'Graph': "{'Mode': 'c', 'Block through centroids': False, 'Number of centroids': 24, 'Links': 76, 'Nodes': 24}","""
        in file_text
    )
    assert (
        """'Number of centroids': 24, 'Matrix cores': ['car'], 'Matrix totals': {'car': 271266.6324170904}}"}}"""
        in file_text
    )
    assert """INFO ; {'motorcycles': {'Graph': "{'Mode': 'M', 'Block through centroids': False, 'Number of centroids': 24, 'Links': 76, 'Nodes': 24}","""
    assert """'Number of centroids': 24, 'Matrix cores': ['motorcycle'], 'Matrix totals': {'motorcycle': 89819.0708124364}}"}}"""
    assert """INFO ; {'trucks': {'Graph': "{'Mode': 'T', 'Block through centroids': False, 'Number of centroids': 24, 'Links': 76, 'Nodes': 24}","""
    assert (
        """'Number of centroids': 24, 'Matrix cores': ['trucks'], 'Matrix totals': {'trucks': 90235.57459796841}}"}}"""
    )
    assert "INFO ; Traffic Assignment specification" in file_text
    assert "{{'VDF parameters': {{'alpha': 0.15, 'beta': 4.0}}, 'VDF function': 'bpr', 'Number of cores': {}, 'Capacity field': 'capacity', 'Time field': 'free_flow_time', 'Algorithm': 'bfw', 'Maximum iterations': 20, 'Target RGAP': 0.001}}".format(
        num_cores
    )


def test_all_or_nothing(ae_with_project, qtbot):
    dialog = TrafficAssignmentDialog(ae_with_project)

    test_name = f"TestTrafficAssignment_AON_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand.aem")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_vdf.setCurrentText("BPR")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("all-or-nothing")

    dialog.run()

    with pytest.raises(ValueError):
        dialog.produce_all_outputs()

    dialog.close()

    pth = Path(dialog.project.project_base_path)
    results = pth / "results_database.sqlite"
    assert isfile(results)

    # Assert we have a non-null result and that results are actually stored in the file
    con = sqlite3.connect(results)
    assert con.execute(f"SELECT ROUND(SUM(matrix_tot), 4) FROM {test_name}").fetchone()[0] == 885_300.0

    skims = pth / f"matrices/{test_name}_car.omx"
    assert isfile(skims)


def test_select_link_analysis(ae_with_project, qtbot):
    dialog = TrafficAssignmentDialog(ae_with_project)

    test_name = f"TestTrafficAssignment_SLA_{uuid4().hex[:6]}"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand.aem")

    # Traffic classes
    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    # Select link
    dialog.do_select_link.setChecked(True)
    dialog.input_qry_name.setText("Leaving from 1")
    dialog.input_link_id.setText("1")
    qtbot.mouseClick(dialog.but_add_query, Qt.LeftButton)
    dialog.input_link_id.setText("2")
    qtbot.mouseClick(dialog.but_add_query, Qt.LeftButton)
    qtbot.mouseClick(dialog.but_build_query, Qt.LeftButton)
    dialog.sl_mat_name.setText("select_link_analysis")

    # Assignment
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_vdf.setCurrentText("BPR")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("25")
    dialog.rel_gap.setText("0.001")

    dialog.run()

    matrices = dialog.project.matrices
    matrices.update_database()
    assert "select_link_analysis.omx" in matrices.list()["file_name"].tolist()

    pth = Path(dialog.project.project_base_path)
    conn = sqlite3.connect(pth / "results_database.sqlite")
    results = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    assert "select_link_analysis" in results


def test_link_removal(ae_with_project, qtbot):
    links = [9, 10, 11, 13, 23, 25, 26, 27, 28, 31, 32, 34, 40, 41, 43, 44]
    layer = ae_with_project.layers["links"][0]
    layer.select([f.id() for f in layer.getFeatures() if f["link_id"] in links])

    dialog = TrafficAssignmentDialog(ae_with_project)

    test_name = "TestTrafficAssignment_LinkRemoval"
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("demand.aem")

    dialog.tbl_core_list.selectRow(0)
    dialog.cob_mode_for_class.setCurrentIndex(0)
    dialog.ln_class_name.setText("car")
    dialog.pce_setter.setValue(1.0)
    dialog.chb_check_centroids.setChecked(False)
    dialog.chb_chosen_links.setChecked(True)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Skimming
    dialog.cob_skims_available.setCurrentText("free_flow_time")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_vdf.setCurrentText("BPR")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("25")
    dialog.rel_gap.setText("0.001")

    dialog.run()

    with pytest.raises(ValueError):
        dialog.produce_all_outputs()

    dialog.close()

    project = ae_with_project.project
    matrices = project.matrices
    matrices.update_database()
    assert f"{test_name}_car" in matrices.list()["name"].values.tolist()

    conn = sqlite3.connect(join(project.project_base_path, "results_database.sqlite"))
    results = pd.read_sql(f"Select link_id, PCE_tot from {test_name}", conn).set_index("link_id")

    for idx, row in results.iterrows():
        if idx in links:
            assert row["PCE_tot"] == 0
        else:
            assert row["PCE_tot"] > 0

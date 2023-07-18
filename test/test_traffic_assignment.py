import numpy as np
import openmatrix as omx
from pathlib import Path
from os.path import isfile
import sqlite3
from uuid import uuid4
from PyQt5.QtCore import QTimer, Qt, QItemSelectionModel
import pytest
from qaequilibrae.modules.matrix_procedures.load_project_data import LoadProjectDataDialog
from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog


def test_ta_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog
    from test.test_qaequilibrae_menu_with_project import check_if_new_active_window_matches_class

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, TrafficAssignmentDialog)

    action = ae_with_project.menuActions["Paths and assignment"][2]
    assert action.text() == "Traffic Assignment", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()

def test_single_class_traffic_assignment(ae_with_project, qtbot):
    update_matrices = LoadProjectDataDialog(ae_with_project)
    update_matrices.update_matrix_table()

    dialog = TrafficAssignmentDialog(ae_with_project)

    test_name = f"TestTrafficAssignment_SC_{uuid4().hex[:6]}"
    dialog.cob_matrices.setCurrentText("demand")
    dialog.ln_class_name.setText("car")
    dialog.cob_mode_for_class.setCurrentText("car (c)")

    dialog.tbl_core_list.selectRow(0)

    dialog.cob_skim_class.setCurrentText("car")
    dialog.chb_check_centroids.setChecked(False)
    dialog.output_scenario_name.setText(test_name)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

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
    dialog.max_iter.setText("500")
    dialog.rel_gap.setText("0.001")

    dialog.run()

    pth = Path("test/data/SiouxFalls_project")
    results = pth / "results_database.sqlite"
    assert isfile(results)

    con = sqlite3.connect(results)
    assert con.execute(f"SELECT ROUND(SUM(PCE_tot), 4) FROM {test_name}").fetchone()[0] == 879087.8481

    skims = pth / ("matrices/" + test_name + "_car.omx")
    assert isfile(skims)

    mtx = omx.open_file(skims)
    assert round(np.sum(np.nan_to_num(mtx["free_flow_time_final"][:])), 4) == 13594.6657
    assert round(np.sum(np.nan_to_num(mtx["free_flow_time_blended"][:])), 4) == 13548.7296
    assert round(np.sum(np.nan_to_num(mtx["distance_final"][:])), 4) == 6584.0
    assert round(np.sum(np.nan_to_num(mtx["distance_blended"][:])), 4) == 6719.0863

    num_cores = dialog.assignment.cores
    log_ = pth / "aequilibrae.log"
    assert isfile(log_)

    file_text = ""
    with open(log_, "r", encoding="utf-8") as file:
        for line in file.readlines():
            file_text += line

    assert "INFO ; Traffic Class specification" in file_text
    assert """INFO ; {'car': {'Graph': "{'Mode': 'c', 'Block through centroids': False, 'Number of centroids': 24, 'Links': 76, 'Nodes': 24}",""" in file_text
    assert """'Number of centroids': 24, 'Matrix cores': ['matrix'], 'Matrix totals': {'matrix': 360600.0}}"}}""" in file_text
    assert "INFO ; Traffic Assignment specification" in file_text
    assert "{{'VDF parameters': {{'alpha': 0.15, 'beta': 4.0}}, 'VDF function': 'bpr', 'Number of cores': {}, 'Capacity field': 'capacity', 'Time field': 'free_flow_time', 'Algorithm': 'bfw', 'Maximum iterations': 30, 'Target RGAP': 0.001}}".format(num_cores)

def test_multiclass_traffic_assignment(ae_with_project, qtbot):
    update_matrices = LoadProjectDataDialog(ae_with_project)

    dialog = TrafficAssignmentDialog(ae_with_project)
    dialog.testing = True

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
    dialog.cob_skims_available.setCurrentIndex(4)
    dialog.cob_skim_class.setCurrentIndex(0)
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentIndex(8)
    dialog.cob_skim_class.setCurrentIndex(0)
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    # Traffic Class Trucks
    dialog.tbl_core_list.selectRow(2)
    dialog.cob_mode_for_class.setCurrentIndex(4)
    dialog.ln_class_name.setText("Trucks")
    dialog.pce_setter.setValue(2.5)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Adds truck skims
    dialog.cob_skims_available.setCurrentIndex(4)
    dialog.cob_skim_class.setCurrentIndex(1)
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentIndex(8)
    dialog.cob_skim_class.setCurrentIndex(1)
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    # Traffic Class Motorcycle
    dialog.tbl_core_list.selectRow(1)
    dialog.cob_mode_for_class.setCurrentIndex(3)
    dialog.cob_mode_for_class.setCurrentText("Motorcycle")
    dialog.pce_setter.setValue(0.2)
    dialog.chb_check_centroids.setChecked(False)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    # Adds motorcycle skims
    dialog.cob_skims_available.setCurrentIndex(4)
    dialog.cob_skim_class.setCurrentIndex(2)
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)
    dialog.cob_skims_available.setCurrentIndex(8)
    dialog.cob_skim_class.setCurrentIndex(2)
    qtbot.mouseClick(dialog.but_add_skim, Qt.LeftButton)

    dialog.skims["car"] = ["free_flow_time", "distance"]
    dialog.skims["Trucks"] = ["free_flow_time", "distance"]
    dialog.skims["Motorcycle"] = ["free_flow_time", "distance"]

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

    pth = Path("test/data/SiouxFalls_project")
    results = pth / "results_database.sqlite"
    assert isfile(results)
    con = sqlite3.connect(results)
    assert con.execute(f"SELECT ROUND(SUM(PCE_tot), 4) FROM {test_name}").fetchone()[0] == 1332054.7483
    assert con.execute(f"SELECT ROUND(SUM(car_tot), 4) FROM {test_name}").fetchone()[0] == 698325.9227
    assert con.execute(f"SELECT ROUND(SUM(motorcycle_tot), 4) FROM {test_name}").fetchone()[0] == 242112.6235
    assert con.execute(f"SELECT ROUND(SUM(trucks_tot), 4) FROM {test_name}").fetchone()[0] == 234122.5204

    assert isfile(pth / ("matrices/" + test_name + "_car.omx"))
    assert isfile(pth / ("matrices/" + test_name + "_Motorcycle.omx"))
    assert isfile(pth / ("matrices/" + test_name + "_Trucks.omx"))

    num_cores = dialog.assignment.cores
    log_ = pth / "aequilibrae.log"
    assert isfile(log_)

    file_text = ""
    with open(log_, "r", encoding="utf-8") as file:
        for line in file.readlines():
            file_text += line

    assert "INFO ; Traffic Class specification" in file_text
    assert """INFO ; {'car': {'Graph': "{'Mode': 'c', 'Block through centroids': False, 'Number of centroids': 24, 'Links': 76, 'Nodes': 24}",""" in file_text
    assert """'Number of centroids': 24, 'Matrix cores': ['car'], 'Matrix totals': {'car': 271266.6324170904}}"}}""" in file_text
    assert """INFO ; {'motorcycles': {'Graph': "{'Mode': 'M', 'Block through centroids': False, 'Number of centroids': 24, 'Links': 76, 'Nodes': 24}","""
    assert """'Number of centroids': 24, 'Matrix cores': ['motorcycle'], 'Matrix totals': {'motorcycle': 89819.0708124364}}"}}"""
    assert """INFO ; {'trucks': {'Graph': "{'Mode': 'T', 'Block through centroids': False, 'Number of centroids': 24, 'Links': 76, 'Nodes': 24}","""
    assert """'Number of centroids': 24, 'Matrix cores': ['trucks'], 'Matrix totals': {'trucks': 90235.57459796841}}"}}"""
    assert "INFO ; Traffic Assignment specification" in file_text
    assert "{{'VDF parameters': {{'alpha': 0.15, 'beta': 4.0}}, 'VDF function': 'bpr', 'Number of cores': {}, 'Capacity field': 'capacity', 'Time field': 'free_flow_time', 'Algorithm': 'bfw', 'Maximum iterations': 20, 'Target RGAP': 0.001}}".format(num_cores)

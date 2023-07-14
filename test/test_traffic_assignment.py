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

    test_name = f"TestTrafficAssignment_{uuid4().hex[:6]}"
    dialog.cob_matrices.setCurrentText("b'none'")
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
    dialog.max_iter.setText("30")
    dialog.rel_gap.setText("0.001")

    dialog.run()

    pth = Path("test/data/SiouxFalls_project")
    results = pth / "results_database.sqlite"
    assert isfile(results)
    con = sqlite3.connect(results)
    assert con.execute(f"SELECT SUM(PCE_tot) FROM {test_name}").fetchone()[0] > 881_000

    skims = pth / ("matrices/" + test_name + "_car.omx")
    assert isfile(skims)

    mtx = omx.open_file(skims)
    assert np.sum(np.nan_to_num(mtx["free_flow_time_final"][:])) > 13_500
    assert np.sum(np.nan_to_num(mtx["free_flow_time_blended"][:])) > 13_500
    assert np.sum(np.nan_to_num(mtx["distance_final"][:])) > 6_500
    assert np.sum(np.nan_to_num(mtx["distance_blended"][:])) > 6_700

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

@pytest.mark.skip(reason="It's not working yet")
def test_multiclass_traffic_assignment(ae_with_project, qtbot):
    update_matrices = LoadProjectDataDialog(ae_with_project)
    update_matrices.update_matrix_table()

    dialog = TrafficAssignmentDialog(ae_with_project)

    test_name = f"TestTrafficAssignment_MC_{uuid4().hex[:6]}"
    print("test_id: ", test_name)
    dialog.output_scenario_name.setText(test_name)
    dialog.cob_matrices.setCurrentText("b''")

    dialog.ln_class_name.setText("car")
    dialog.cob_mode_for_class.setCurrentText("car (c)")
    dialog.tbl_core_list.selectRow(0)
    dialog.chb_check_centroids.setChecked(False)
    dialog.pce_setter.setValue(1.0)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    dialog.ln_class_name.setText("motorcycle")
    dialog.cob_mode_for_class.setCurrentIndex(3)
    dialog.tbl_core_list.selectRow(1)
    dialog.chb_check_centroids.setChecked(False)
    dialog.pce_setter.setValue(0.2)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    dialog.ln_class_name.setText("truck")
    dialog.cob_mode_for_class.setCurrentText("trucks (T)")
    dialog.cob_mode_for_class.setCurrentIndex(4)
    dialog.tbl_core_list.selectRow(2)
    dialog.chb_check_centroids.setChecked(False)
    dialog.pce_setter.setValue(2.5)
    qtbot.mouseClick(dialog.but_add_class, Qt.LeftButton)

    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")
    dialog.cob_vdf.setCurrentText("BPR")
    dialog.cob_capacity.setCurrentText("capacity")
    dialog.cob_ffttime.setCurrentText("free_flow_time")
    dialog.cb_choose_algorithm.setCurrentText("bfw")
    dialog.max_iter.setText("30")
    dialog.rel_gap.setText("0.001")

    dialog.run()

    pth = Path("test/data/SiouxFalls_project")
    results = pth / "results_database.sqlite"
    assert isfile(results)
    con = sqlite3.connect(results)
    assert con.execute(f"SELECT SUM(PCE_tot) FROM {test_name}").fetchone()[0] > 152_000
    assert con.execute(f"SELECT SUM(car_tot) FROM {test_name}").fetchone()[0] > 81_000
    assert con.execute(f"SELECT SUM(motorcycle_tot) FROM {test_name}").fetchone()[0] > 27_000
    assert con.execute(f"SELECT SUM(trucks_tot) FROM {test_name}").fetchone()[0] > 26_000

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
    # Check for motorcycle and truck

    assert "INFO ; Traffic Assignment specification" in file_text
    assert "{{'VDF parameters': {{'alpha': 0.15, 'beta': 4.0}}, 'VDF function': 'bpr', 'Number of cores': {}, 'Capacity field': 'capacity', 'Time field': 'free_flow_time', 'Algorithm': 'bfw', 'Maximum iterations': 30, 'Target RGAP': 0.001}}".format(num_cores)

import sqlite3
from os.path import isfile
from os import remove
from pathlib import Path

import numpy as np
import openmatrix as omx
import pytest
from PyQt5.QtCore import QTimer, Qt

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
    

def test_ipf(ae_with_project, qtbot):
    dialog = DistributionModelsDialog(ae_with_project, mode="ipf", testing=True)

    # dialog.dataset_name = "test/data/SiouxFalls_project/synthetic_future_vector.aed" # not currently loaded
    dialog.out_name = "test/data/SiouxFalls_project/demand_ipf.aem"
    dialog.dlg2.dataset.file_path = "test/data/SiouxFalls_project/synthetic_future_vector.aed"
    dialog.load_datasets()

    temp = list(dialog.matrices["name"])
    demand_idx = temp.index("omx")
    dialog.cob_seed_mat.setCurrentIndex(demand_idx)
    dialog.cob_seed_field.setCurrentText("matrix")
    
    dialog.cob_prod_data.setCurrentText("synthetic_future_vector")
    dialog.cob_prod_field.setCurrentText("origins")
    dialog.cob_atra_data.setCurrentText("synthetic_future_vector")
    dialog.cob_atra_field.setCurrentText("destinations")

    # em check data tem as verificações dos vetores estão erradas pq não tem indice?

    qtbot.mouseClick(dialog.but_queue, Qt.LeftButton)
    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    dialog.close()

    assert isfile(dialog.out_name)

@pytest.mark.parametrize(("is_negative", "is_power", "file1", "file2", "ext"), 
    [(True, False, "mod_negative_exponential", "", "A"),
    (False, True, "", "mod_inverse_power", "B"),
    (True, True, "mod_negative_exponential", "mod_inverse_power", "C")])
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

@pytest.mark.skip()
def test_apply_gravity(ae_with_project, qtbot):
    dialog = DistributionModelsDialog(ae_with_project, mode="apply", testing=True)

    dialog.path = "test/data/SiouxFalls_project/"
    dialog.cob_imped_mat.setCurrentIndex(5)
    dialog.cob_imped_field.setCurrentText("free_flow_time_final")

    qtbot.mouseClick(dialog.but_queue, Qt.LeftButton)
    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    dialog.close()
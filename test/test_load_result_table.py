import pytest
from time import sleep
from PyQt5.QtCore import Qt

from qaequilibrae.modules.matrix_procedures.load_result_table import load_result_table


def run_traffic_assignment(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog
    dialog = TrafficAssignmentDialog(ae_with_project)

    assignment_result = f"TrafficAssignment_DP_LRT"
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


# @pytest.mark.skip("Not working")
def test_load_result_table(ae_with_project, qtbot):
    # run_traffic_assignment(ae_with_project, qtbot)

    # sleep(10)
    print("here")
    layer = load_result_table(ae_with_project.project.project_base_path, "TrafficAssignment_DP_LRT")

    assert layer.isValid()

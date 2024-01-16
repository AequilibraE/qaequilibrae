import pytest

from qaequilibrae.modules.matrix_procedures.load_result_table import load_result_table


@pytest.mark.skip("not working")
def test_load_result_table(ae_with_project, run_traffic_assignment, qtbot):

    run_traffic_assignment(ae_with_project, qtbot, "LTR")

    layer = load_result_table(ae_with_project.project.project_base_path, "TrafficAssignment_DP_LTR")

    assert layer.isValid()

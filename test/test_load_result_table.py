import pytest

from qaequilibrae.modules.matrix_procedures.load_result_table import load_result_table


@pytest.mark.skip("Not working")
def test_load_result_table(ae_with_project):

    layer = load_result_table(ae_with_project.project.project_base_path, "TrafficAssignment_DP_A")

    assert layer.isValid()

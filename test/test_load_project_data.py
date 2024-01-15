import pytest

from qaequilibrae.modules.matrix_procedures.load_project_data import LoadProjectDataDialog


@pytest.fixture
def dialog(ae_with_project):
    dialog = LoadProjectDataDialog(ae_with_project)
    return dialog


@pytest.mark.skip(reason="Test is not working")
def test_update_matrix_table(dialog):
    dialog.update_matrix_table()

import pytest
import sys
from os.path import isfile

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox, QTabWidget
from qgis.core import QgsProject

from qaequilibrae.modules.matrix_procedures.load_project_data import LoadProjectDataDialog
from .utilities import run_sfalls_assignment


pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Running on Windows")


def test_no_project(ae, mocker, qtbot):
    file_func = "qaequilibrae.modules.matrix_procedures.load_project_data.DisplayAequilibraEFormatsDialog"
    mocker.patch(file_func)

    dialog = LoadProjectDataDialog(ae, False)

    assert QTabWidget.tabText(dialog.tabs, 0) == "Non-project Data"

    qtbot.mouseClick(dialog.but_load_data, Qt.MouseButton.LeftButton)
    dialog.close()


# TODO: Re-write the tests - they're really time consuming
@pytest.mark.parametrize("button_clicked", [True, False])
def test_project(sf_project, mocker, qtbot, button_clicked):
    proj = run_sfalls_assignment(sf_project)

    function = "qaequilibrae.modules.matrix_procedures.load_project_data.DisplayAequilibraEFormatsDialog"
    mocker.patch(function)

    dialog = LoadProjectDataDialog(proj, True)

    assert QTabWidget.tabText(dialog.tabs, 0) == "Matrices"
    assert QTabWidget.tabText(dialog.tabs, 1) == "Results"
    assert QTabWidget.tabText(dialog.tabs, 2) == "Non-project Data"

    qtbot.mouseClick(dialog.but_update_matrices, Qt.MouseButton.LeftButton)

    assert "assignment_car.omx" in dialog.matrices["file_name"].tolist()

    # Select matrix row to display
    dialog.list_matrices.selectRow(0)
    qtbot.mouseClick(dialog.but_load_matrix, Qt.MouseButton.LeftButton)

    # Result selection
    dialog.list_results.selectRow(0)
    qtbot.mouseClick(dialog.but_load_Results, Qt.MouseButton.LeftButton)

    existing_layers = [vector.name() for vector in QgsProject.instance().mapLayers().values()]
    assert "assignment" in existing_layers

    # assert data from table was properly joined in links layer
    results_fields = [
        "matrix_ab",
        "matrix_ba",
        "matrix_tot",
        "Congested_Time_AB",
        "Congested_Time_BA",
        "Congested_Time_Max",
        "Delay_factor_AB",
        "Delay_factor_BA",
        "Delay_factor_Max",
        "VOC_AB",
        "VOC_BA",
        "VOC_max",
        "PCE_AB",
        "PCE_BA",
        "PCE_tot",
    ]
    if button_clicked:
        layer = QgsProject.instance().mapLayersByName("links")[0]
        field_names = [field.name() for field in layer.fields()]
        for r in results_fields:
            assert "assignment_" + r in field_names

    dialog.close()


def double_click(table, row):
    """Fires a table view's own doubleClicked signal for one row.

    These tests never show the dialog, so the views have no geometry to aim a real double-click
    at. Going through the signal still exercises the connection and everything behind it.
    """
    table.doubleClicked.emit(table.model().index(row, 0))


def test_declining_the_prompt_leaves_the_matrix_alone(ae_with_project, mocker):
    dialog = LoadProjectDataDialog(ae_with_project, True)
    question = mocker.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No)

    matrix_name = dialog.matrices["name"].iloc[0]
    matrix_file = dialog.project.project_base_path / "matrices" / dialog.matrices["file_name"].iloc[0]

    double_click(dialog.list_matrices, 0)

    # The box has to come up with No selected, so that dismissing it cannot delete anything
    assert question.call_args.args[-1] == QMessageBox.StandardButton.No
    assert matrix_name in dialog.matrices["name"].tolist()
    assert isfile(matrix_file)

    dialog.close()


def test_confirming_deletes_the_matrix_and_its_file(ae_with_project, mocker):
    dialog = LoadProjectDataDialog(ae_with_project, True)
    mocker.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes)

    matrix_file = dialog.project.project_base_path / "matrices" / dialog.matrices["file_name"].iloc[0]
    remaining = dialog.matrices["name"].tolist()[1:]

    double_click(dialog.list_matrices, 0)

    assert dialog.matrices["name"].tolist() == remaining
    assert not isfile(matrix_file)

    dialog.close()


def test_a_result_is_only_deleted_once_the_prompt_is_confirmed(sf_project, mocker):
    proj = run_sfalls_assignment(sf_project)

    dialog = LoadProjectDataDialog(proj, True)
    question = mocker.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No)

    table_name = dialog.results["table_name"].iloc[0]

    double_click(dialog.list_results, 0)

    assert question.call_args.args[-1] == QMessageBox.StandardButton.No
    assert table_name in dialog.results["table_name"].tolist()

    question.return_value = QMessageBox.StandardButton.Yes
    double_click(dialog.list_results, 0)

    assert table_name not in dialog.results["table_name"].tolist()
    with dialog.project.results_connection as conn:
        tables = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert table_name not in tables

    dialog.close()

import pytest
import sys
from PyQt5.QtCore import Qt
from qgis.PyQt.QtWidgets import QTabWidget
from qgis.core import QgsProject

from qaequilibrae.modules.matrix_procedures.load_project_data import LoadProjectDataDialog
from .utilities import run_sfalls_assignment


pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Running on Windows")


def test_no_project(ae, mocker, qtbot):
    file_func = "qaequilibrae.modules.matrix_procedures.load_project_data.DisplayAequilibraEFormatsDialog"
    mocker.patch(file_func)

    dialog = LoadProjectDataDialog(ae, False)

    assert QTabWidget.tabText(dialog.tabs, 0) == "Non-project Data"

    qtbot.mouseClick(dialog.but_load_data, Qt.LeftButton)
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

    qtbot.mouseClick(dialog.but_update_matrices, Qt.LeftButton)

    assert "assignment_car.omx" in dialog.matrices["file_name"].tolist()

    # Select matrix row to display
    dialog.list_matrices.selectRow(0)
    qtbot.mouseClick(dialog.but_load_matrix, Qt.LeftButton)

    # Result selection
    dialog.list_results.selectRow(0)
    qtbot.mouseClick(dialog.but_load_Results, Qt.LeftButton)

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

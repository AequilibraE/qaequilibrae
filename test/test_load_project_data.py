import pytest
from PyQt5.QtCore import Qt
from qgis.PyQt.QtWidgets import QAbstractItemView, QTabWidget
from qaequilibrae.modules.matrix_procedures.load_project_data import LoadProjectDataDialog


def test_no_project(ae, mocker, qtbot):
    file_func = "qaequilibrae.modules.matrix_procedures.load_project_data.LoadProjectDataDialog.display_external_data"
    mocker.patch(file_func)

    dialog = LoadProjectDataDialog(ae, False)

    assert QTabWidget.tabText(dialog.tabs, 0) == "Non-project Data"

    qtbot.mouseClick(dialog.but_load_data, Qt.LeftButton)
    dialog.close()


def test_project(ae_with_project, mocker, qtbot):
    function = "qaequilibrae.modules.matrix_procedures.load_project_data.DisplayAequilibraEFormatsDialog"
    mocker.patch(function)

    dialog = LoadProjectDataDialog(ae_with_project, True)

    assert QTabWidget.tabText(dialog.tabs, 0) == "Matrices"
    assert QTabWidget.tabText(dialog.tabs, 1) == "Results"
    assert QTabWidget.tabText(dialog.tabs, 2) == "Non-project Data"

    # It should have different matrices in the folder to update.
    qtbot.mouseClick(dialog.but_update_matrices, Qt.LeftButton)

    # Select matrix row to display
    # self.list_matrices.selectionModel().selectedRows()
    qtbot.mouseClick(dialog.but_load_matrix, Qt.LeftButton)

    # Result selection
    # self.list_results.selectionModel().selectedRows()
    qtbot.mouseClick(dialog.but_load_Results, Qt.LeftButton)

    # assert there is an open data table
    # assert data from table was properly joined in links layer

    dialog.close()

    # print(dialog.__dict__)

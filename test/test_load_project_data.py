import pytest
from os.path import join
from shutil import copyfile
from PyQt5.QtCore import Qt
from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QTabWidget
from qaequilibrae.modules.matrix_procedures.load_project_data import LoadProjectDataDialog


@pytest.fixture
def run_aon(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog

    dialog = TrafficAssignmentDialog(ae_with_project)

    assignment_result = "aon"
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
    dialog.cb_choose_algorithm.setCurrentText("aon")
    dialog.max_iter.setText("1")
    dialog.rel_gap.setText("0.001")
    dialog.tbl_vdf_parameters.cellWidget(0, 1).setText("0.15")
    dialog.tbl_vdf_parameters.cellWidget(1, 1).setText("4.0")

    dialog.run()

    return ae_with_project


def test_no_project(ae, mocker, qtbot):
    file_func = "qaequilibrae.modules.matrix_procedures.load_project_data.DisplayAequilibraEFormatsDialog"
    mocker.patch(file_func)

    dialog = LoadProjectDataDialog(ae, False)

    assert QTabWidget.tabText(dialog.tabs, 0) == "Non-project Data"

    qtbot.mouseClick(dialog.but_load_data, Qt.LeftButton)
    dialog.close()


@pytest.mark.parametrize("button_clicked", [True, False])
def test_project(run_aon, mocker, qtbot, button_clicked):
    proj = run_aon

    function = "qaequilibrae.modules.matrix_procedures.load_project_data.DisplayAequilibraEFormatsDialog"
    mocker.patch(function)

    dialog = LoadProjectDataDialog(proj, True)

    assert QTabWidget.tabText(dialog.tabs, 0) == "Matrices"
    assert QTabWidget.tabText(dialog.tabs, 1) == "Results"
    assert QTabWidget.tabText(dialog.tabs, 2) == "Non-project Data"

    # It should have different matrices in the folder to update.
    proj_folder = dialog.project.project_base_path
    copyfile(join(proj_folder, "matrices/sfalls_skims.omx"), join(proj_folder, "matrices/new_sfskim.omx"))

    qtbot.mouseClick(dialog.but_update_matrices, Qt.LeftButton)

    assert "new_sfskim.omx" in dialog.matrices["file_name"].tolist()

    # Select matrix row to display
    dialog.list_matrices.selectRow(0)
    qtbot.mouseClick(dialog.but_load_matrix, Qt.LeftButton)

    assert dialog.matrices["file_name"][0] == "sfalls_skims.omx"

    # Result selection
    dialog.list_results.selectRow(0)
    qtbot.mouseClick(dialog.but_load_Results, Qt.LeftButton)

    existing_layers = [vector.name() for vector in QgsProject.instance().mapLayers().values()]
    assert "aon" in existing_layers

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
            assert "aon_" + r in field_names

    print(dialog.__dict__)

    dialog.close()

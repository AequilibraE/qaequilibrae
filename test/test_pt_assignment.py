from os.path import join

import numpy as np
import pandas as pd
import pytest
from qgis.PyQt.QtCore import Qt, QTime
from qgis.PyQt.QtWidgets import QDialog

from qaequilibrae.modules.matrix_procedures.load_result_table import load_result_table
from qaequilibrae.modules.public_transport_procedures.new_period_dialog import NewPeriodDialog
from qaequilibrae.modules.public_transport_procedures.transit_assignment_dialog import TransitAssignDialog
from .utilities import create_matrix


def create_dialog_with_matrix(project):
    pth = join(project.project.project_base_path, "matrices/demand.aem")
    create_matrix(np.arange(1, 134), pth)

    matrices = project.project.matrices
    matrices.update_database()
    matrices.reload()

    return TransitAssignDialog(project)


def test_assignment(qtbot, coquimbo_project):
    dialog = create_dialog_with_matrix(coquimbo_project)

    # select period
    dialog.tbl_periods.selectRow(0)

    # set transit graph config
    dialog.chb_walk_edges.setChecked(False)
    dialog.chb_check_centroids.setChecked(False)
    dialog.cob_conn_methods.setCurrentText("Nearest neighbour")
    dialog.cob_line_methods.setCurrentText("Connector project match")

    # Add boardings, alightings, and transfers
    for row in [0, 0, 2]:
        dialog.available_skims_table.selectRow(row)
        qtbot.mouseClick(dialog.but_adds_to_skim, Qt.LeftButton)

    assert dialog.skim_fields == ["boardings", "alightings", "transfers"]

    dialog.ln_transit_class.setText("pt_class")
    dialog.cob_travel_time.setCurrentText("trav_time")
    dialog.cob_freq.setCurrentText("freq")
    dialog.ln_result_name.setText("pt_assignment")

    qtbot.mouseClick(dialog.but_assign, Qt.LeftButton)

    # Check the results table
    result = load_result_table(coquimbo_project.project.project_base_path, "pt_assignment")
    assert result.shape == (466, 2)
    assert result.columns.tolist() == ["index", "pt_class_volume"]

    # check if graph was saved
    with coquimbo_project.project.db_connection as conn:
        df = pd.read_sql("SELECT * FROM transit_graph_configs", con=conn)
    assert df.shape == (1, 2)
    config = df.iloc[0]["config"]
    assert (
        config
        == """{"period_id": 1, "projected_crs": "EPSG:3857", "seed": 124, "geometry_noise": true, "noise_coef": 1e-05, "with_inner_stop_transfers": false, "with_outer_stop_transfers": false, "with_walking_edges": false, "distance_upper_bound": Infinity, "blocking_centroid_flows": false, "connector_method": "nearest_neighbour", "max_connectors_per_zone": -1}"""
    )


def test_skimming(qtbot, coquimbo_project):
    dialog = create_dialog_with_matrix(coquimbo_project)

    # select period
    dialog.tbl_periods.selectRow(0)

    # set transit graph config
    dialog.chb_check_centroids.setChecked(False)
    dialog.chb_walk_edges.setChecked(False)
    dialog.chb_save_graph.setChecked(False)

    # Add boardings, dwelling_time, and transfer_time
    for row in [0, 6, 9]:
        dialog.available_skims_table.selectRow(row)
        qtbot.mouseClick(dialog.but_adds_to_skim, Qt.LeftButton)

    assert dialog.skim_fields == ["boardings", "dwelling_time", "transfer_time"]

    # Remove dwelling_time
    dialog.skim_list.selectRow(1)
    qtbot.mouseClick(dialog.but_removes_from_skim, Qt.LeftButton)

    assert dialog.skim_fields == ["boardings", "transfer_time"]

    dialog.ln_matrix_name.setText("selected_pt_skims")

    qtbot.mouseClick(dialog.but_create, Qt.LeftButton)

    matrices = coquimbo_project.project.matrices
    matrices.update_database()
    mats = matrices.list()
    selected_matrix = mats[mats["file_name"] == "selected_pt_skims.omx"]
    assert not selected_matrix.empty, "Matrix with file_name 'selected_pt_skims.omx' not found."
    assert selected_matrix.iloc[0]["file_name"] == "selected_pt_skims.omx"

    mat = matrices.get_matrix("selected_pt_skims_omx")
    assert mat.cores == 2
    assert mat.names == ["boardings", "transfer_time"]


@pytest.fixture
def mock_period(mocker):
    """Mock patch for NewPeriodDialog"""
    dialog = mocker.Mock(spec=QDialog)
    dialog.start_time = 24_300
    dialog.end_time = 34_200
    dialog.description = "From 6:45AM to 9:30AM"
    dialog.error = []

    mocker.patch(
        "qaequilibrae.modules.public_transport_procedures.transit_assignment_dialog.NewPeriodDialog",
        return_value=dialog,
    )

    return dialog


def test_create_period(qtbot, coquimbo_project, mock_period):
    dialog = create_dialog_with_matrix(coquimbo_project)
    qtbot.mouseClick(dialog.but_add_period, Qt.LeftButton)

    periods = dialog.project.network.periods
    assert periods.data.shape[0] == 2

    dialog.tbl_periods.selectRow(1)

    period_id = dialog.get_period()
    assert period_id == 2


def test_new_period_dialog(qgis_iface):
    dialog = NewPeriodDialog(qgis_iface)

    # Set the start and end times
    start_time = QTime(6, 45)  # 6:45 AM
    end_time = QTime(9, 30)  # 9:30 AM

    dialog.time_start.setTime(start_time)
    dialog.time_end.setTime(end_time)
    dialog.ln_period_desc.setText("Custom period")

    assert dialog.time_start.time() == start_time, "Start time is different than expected."
    assert dialog.time_end.time() == end_time, "End time is different than expected."


def test_period_not_selected(qtbot, coquimbo_project):
    dialog = create_dialog_with_matrix(coquimbo_project)

    dialog.available_skims_table.selectRow(0)
    qtbot.mouseClick(dialog.but_adds_to_skim, Qt.LeftButton)

    dialog.ln_matrix_name.setText("selected_pt_skims")

    qtbot.mouseClick(dialog.but_create, Qt.LeftButton)

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == "Warning:Please select a period"


def test_no_skims(qtbot, coquimbo_project):
    dialog = create_dialog_with_matrix(coquimbo_project)
    dialog.tbl_periods.selectRow(0)

    dialog.ln_matrix_name.setText("selected_pt_skims")

    qtbot.mouseClick(dialog.but_create, Qt.LeftButton)

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == "Warning:Add skims to the selection"


@pytest.mark.parametrize("name", ["", "     "])
def test_no_matrix_name(qtbot, coquimbo_project, name):
    dialog = create_dialog_with_matrix(coquimbo_project)
    dialog.tbl_periods.selectRow(0)

    dialog.available_skims_table.selectRow(0)
    qtbot.mouseClick(dialog.but_adds_to_skim, Qt.LeftButton)

    dialog.ln_matrix_name.setText(name)

    qtbot.mouseClick(dialog.but_create, Qt.LeftButton)

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == "Warning:Check matrix_name"


@pytest.mark.parametrize("name", ["", "     "])
def test_no_pt_class_name(qtbot, coquimbo_project, name):
    dialog = create_dialog_with_matrix(coquimbo_project)
    dialog.tbl_periods.selectRow(0)

    dialog.ln_transit_class.setText(name)

    dialog.ln_result_name.setText("pt_assignment")

    qtbot.mouseClick(dialog.but_assign, Qt.LeftButton)

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == "Warning:Check PT class name"


@pytest.mark.parametrize("name", ["", "     "])
def test_no_results_name(qtbot, coquimbo_project, name):
    dialog = create_dialog_with_matrix(coquimbo_project)
    dialog.tbl_periods.selectRow(0)

    dialog.ln_transit_class.setText("pt_class")

    dialog.ln_result_name.setText(name)

    qtbot.mouseClick(dialog.but_assign, Qt.LeftButton)

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == "Warning:Check result_name"

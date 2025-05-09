from os.path import join

import numpy as np
import pytest
from qgis.PyQt.QtCore import Qt, QTime
from qgis.PyQt.QtWidgets import QDialog

from qaequilibrae.modules.public_transport_procedures.new_period_dialog import NewPeriodDialog
from qaequilibrae.modules.public_transport_procedures.transit_skimming_and_assignment import TransitSkimAssign
from .utilities import create_matrix


def create_dialog_with_matrix(project):
    pth = join(project.project.project_base_path, "matrices/demand.aem")
    create_matrix(np.arange(1, 134), pth)

    matrices = project.project.matrices
    matrices.update_database()
    matrices.reload()

    return TransitSkimAssign(project)


def test_init(qtbot, coquimbo_project):
    dialog = create_dialog_with_matrix(coquimbo_project)

    # select period
    dialog.tbl_periods.selectRow(0)

    # set transit graph config
    dialog.chb_inner_stops.setChecked(True)

    # Add boardings, dwelling_time, and transfer_time
    for row in [0, 6, 9]:
        dialog.available_skims_table.selectRow(row)  # add boardings
        dialog.append_to_list()
    
    assert dialog.skim_fields == ["boardings", "dwelling_time", "transfer_time"]

    # Remove dwelling_time
    dialog.skim_list.selectRow(1)
    dialog.removes_fields()

    assert dialog.skim_fields == ["boardings", "transfer_time"]

    dialog.ln_matrix_name.setText("selected_pt_skims")

    dialog.run("create")

    for i in [0, 1, 2, 3]:
        path = qtbot.screenshot(dialog.tabWidget.widget(i), suffix=f"{i}")
        print(path)

    matrices = coquimbo_project.project.matrices
    matrices.update_database()
    mats = matrices.list()
    assert mats.iloc[1]["file_name"] == "selected_pt_skims.omx"

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
        "qaequilibrae.modules.public_transport_procedures.transit_skimming_and_assignment.NewPeriodDialog",
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


def test_new_period_dialog(qtbot, qgis_iface):
    dialog = NewPeriodDialog(qgis_iface)

    # Set the start and end times
    start_time = QTime(6, 45)  # 6:45 AM
    end_time = QTime(9, 30)  # 9:30 AM

    dialog.time_start.setTime(start_time)
    dialog.time_end.setTime(end_time)
    dialog.ln_period_desc.setText("Custom period")

    assert dialog.time_start.time() == start_time, "Start time is different than expected."
    assert dialog.time_end.time() == end_time, "End time is different than expected."

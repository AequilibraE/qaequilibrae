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

    for i in [0, 1, 2, 3]:
        path = qtbot.screenshot(dialog.tabWidget.widget(i), suffix=f"{i}")
        print(path)


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

    path = qtbot.screenshot(dialog.tabWidget.widget(0))
    print(path)

    dialog.get_period()


def test_dialog(qtbot, qgis_iface):
    dialog = NewPeriodDialog(qgis_iface)

    # Set the start and end times
    start_time = QTime(6, 45)  # 6:45 AM
    end_time = QTime(9, 30)  # 9:30 AM

    dialog.time_start.setTime(start_time)
    dialog.time_end.setTime(end_time)
    dialog.ln_period_desc.setText("Custom period")

    assert dialog.time_start.time() == start_time, "Start time is different than expected."
    assert dialog.time_end.time() == end_time, "End time is different than expected."

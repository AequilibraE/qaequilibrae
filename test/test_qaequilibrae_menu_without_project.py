import pytest
import sys
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication


pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Running on Windows")


def wait_for_active_window(qtbot):
    timeout = 3000
    window = QApplication.activeWindow()
    while window is None and timeout > 0:
        window = QApplication.activeWindow()
        qtbot.wait(100)
        timeout -= 100
    assert timeout > 0, "Waiting for window to open timed out after 3 seconds"
    return window


def check_if_new_active_window_matches_class(qtbot, windowClass):
    dialog = wait_for_active_window(qtbot)
    try:
        assert isinstance(dialog, windowClass), "Active window does not match the correct window class"
    finally:
        dialog.close()
        assert QApplication.activeWindow() is None, "Dialog window did not close properly"


def test_open_project_menu(ae, qtbot):
    """Testing open project menu
    TODO: find a way to capture and close the open QFileDialog"""
    # def handle_trigger():
    #     check_if_new_active_window_matches_class(qtbot, QFileDialog)
    action = ae.menuActions["Project"][0]
    assert action.text() == "Open project", "Wrong text content"
    # QTimer.singleShot(10, handle_trigger)
    # action.trigger()


def test_run_module_menu(ae, qtbot):
    action = next((a for a in ae.menuActions["Project"] if a.text() == "Run procedures"), None)
    assert action is not None, "Menu action 'Run procedures' not found"
    assert action.text() == "Run procedures", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_scenarios_menu(ae, qtbot):
    action = next((a for a in ae.menuActions["Project"] if a.text() == "Scenarios"), None)
    assert action is not None, "Menu action 'Scenarios' not found"
    assert action.text() == "Scenarios", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_trip_distribution_menu(ae, qtbot):
    action = ae.menuActions["Trip distribution"][0]
    assert action.text() == "Trip distribution", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_shortest_path_menu(ae, qtbot):
    action = ae.menuActions["Path computation"][0]
    assert action.text() == "Shortest path", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_impedance_matrix_menu(ae, qtbot):
    action = ae.menuActions["Path computation"][1]
    assert action.text() == "Impedance matrix", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_skim_viewer_menu(ae, qtbot):
    action = ae.menuActions["Path computation"][2]
    assert action.text() == "Skim viewer", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_traffic_assignment_menu(ae, qtbot):
    action = ae.menuActions["Traffic assignment"][0]
    assert action.text() == "Traffic assignment", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_route_choice_menu(ae, qtbot):
    action = ae.menuActions["Route choice"][0]
    assert action.text() == "Route choice", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_gis_desire_lines_menu(ae, qtbot):
    from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, DesireLinesDialog)

    action = ae.menuActions["Mapping"][1]
    assert action.text() == "Desire lines", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_gis_stacked_bandwidth_menu(ae, qtbot):
    from qaequilibrae.modules.gis import CreateBandwidthsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, CreateBandwidthsDialog)

    action = ae.menuActions["Mapping"][2]
    assert action.text() == "Stacked bandwidth", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_gis_scenario_comparison_menu(ae, qtbot):
    action = ae.menuActions["Mapping"][3]
    assert action.text() == "Scenario comparison", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_help_menu(ae, qtbot):
    """TODO: find a way to capture the opening of webpage"""
    button = ae.menuActions["AequilibraE"][0]
    assert button.text() == "Help", "Wrong text content"


def test_gtfs_importer(ae, qtbot):
    action = ae.menuActions["Transit"][0]
    assert action.text() == "Import GTFS", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_pt_skim_and_assign(ae, qtbot):
    action = ae.menuActions["Transit"][1]
    assert action.text() == "Skimming and assignment", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_gtfs_explorer(ae, qtbot):
    action = ae.menuActions["Transit"][2]
    assert action.text() == "Explore transit", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"

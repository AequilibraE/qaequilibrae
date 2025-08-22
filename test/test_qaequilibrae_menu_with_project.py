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


def test_load_project(ae_with_project):
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)
    assert ae_with_project.project is not None, "project should be loaded"


def test_run_module_menu(coquimbo_project, qtbot):
    from qaequilibrae.modules.project_procedures import RunModuleDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, RunModuleDialog)

    action = coquimbo_project.menuActions["Project"][1]
    assert action.text() == "Run procedures", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = coquimbo_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_trip_distribution_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.distribution_procedures import DistributionModelsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, DistributionModelsDialog)

    action = ae_with_project.menuActions["Trip distribution"][0]
    assert action.text() == "Trip distribution", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_shortest_path_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.show_shortest_path_dialog import ShortestPathDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, ShortestPathDialog)

    action = ae_with_project.menuActions["Path computation"][0]
    assert action.text() == "Shortest path", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_impedance_matrix_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.impedance_matrix_dialog import ImpedanceMatrixDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, ImpedanceMatrixDialog)

    action = ae_with_project.menuActions["Path computation"][1]
    assert action.text() == "Impedance matrix", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_skim_viewer_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.skim_viewer_dialog import SkimViewerDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, SkimViewerDialog)

    action = ae_with_project.menuActions["Path computation"][2]
    assert action.text() == "Skim viewer", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_traffic_assignment_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, TrafficAssignmentDialog)

    action = ae_with_project.menuActions["Traffic assignment"][0]
    assert action.text() == "Traffic assignment", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_route_choice_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.route_choice_dialog import RouteChoiceDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, RouteChoiceDialog)

    action = ae_with_project.menuActions["Route choice"][0]
    assert action.text() == "Route choice", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_display_project_data_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.matrix_procedures import LoadProjectDataDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LoadProjectDataDialog)

    action = ae_with_project.menuActions["Mapping"][0]
    assert action.text() == "Visualize data", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_desire_lines_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, DesireLinesDialog)

    action = ae_with_project.menuActions["Mapping"][1]
    assert action.text() == "Desire lines", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_stacked_bandwidth_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.gis import CreateBandwidthsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, CreateBandwidthsDialog)

    action = ae_with_project.menuActions["Mapping"][2]
    assert action.text() == "Stacked bandwidth", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_scenario_comparison_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.gis import CompareScenariosDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, CompareScenariosDialog)

    action = ae_with_project.menuActions["Mapping"][3]
    assert action.text() == "Scenario comparison", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gtfs_importer(ae_with_project, qtbot):
    from qaequilibrae.modules.transit_procedures.gtfs_importer import GTFSImporter

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, GTFSImporter)

    action = ae_with_project.menuActions["Transit"][0]
    assert action.text() == "Import GTFS", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gtfs_explorer(ae_with_project, qtbot):
    action = ae_with_project.menuActions["Transit"][2]
    assert action.text() == "Explore transit", "Wrong text content"
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to import a GTFS feed first", "Level 3 error message is missing"

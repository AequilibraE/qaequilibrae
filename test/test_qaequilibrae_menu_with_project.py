import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis
from aequilibrae_menu import AequilibraEMenu


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


def test_add_zoning_data_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.project_procedures import AddZonesDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, AddZonesDialog)

    action = ae_with_project.menuActions["Project"][3]
    assert action.text() == "Add zoning data", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_parameters_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.common_tools import ParameterDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, ParameterDialog)

    action = ae_with_project.menuActions["Project"][4]
    assert action.text() == "Parameters", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_logfile_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.common_tools import LogDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LogDialog)

    action = ae_with_project.menuActions["Project"][5]
    assert action.text() == "logfile", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_network_preparation_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.network import NetworkPreparationDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, NetworkPreparationDialog)

    action = ae_with_project.menuActions["Network Manipulation"][0]
    assert action.text() == "Network Preparation", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_add_centroid_connectors_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.network import AddConnectorsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, AddConnectorsDialog)

    action = ae_with_project.menuActions["Network Manipulation"][1]
    assert action.text() == "Add centroid connectors", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_display_project_data_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.matrix_procedures import LoadProjectDataDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LoadProjectDataDialog)

    action = ae_with_project.menuActions["Data"][0]
    assert action.text() == "Display project data", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_import_matrices_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.matrix_procedures import LoadMatrixDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LoadMatrixDialog)

    action = ae_with_project.menuActions["Data"][1]
    assert action.text() == "Import matrices", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_trip_distribution_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.distribution_procedures import DistributionModelsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, DistributionModelsDialog)

    action = ae_with_project.menuActions["Trip Distribution"][0]
    assert action.text() == "Trip Distribution", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_shortest_path_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.show_shortest_path_dialog import ShortestPathDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, ShortestPathDialog)

    action = ae_with_project.menuActions["Paths and assignment"][0]
    assert action.text() == "Shortest path", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_impedance_matrix_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.impedance_matrix_dialog import ImpedanceMatrixDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, ImpedanceMatrixDialog)

    action = ae_with_project.menuActions["Paths and assignment"][1]
    assert action.text() == "Impedance matrix", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_traffic_assignment_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, TrafficAssignmentDialog)

    action = ae_with_project.menuActions["Paths and assignment"][2]
    assert action.text() == "Traffic Assignment", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_travelling_salesman_problem_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.routing_procedures import TSPDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, TSPDialog)

    action = ae_with_project.menuActions["Routing"][0]
    assert action.text() == "Travelling Salesman Problem", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_desire_lines_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, DesireLinesDialog)

    action = ae_with_project.menuActions["GIS"][0]
    assert action.text() == "Desire Lines", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_stacked_bandwidth_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.gis import CreateBandwidthsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, CreateBandwidthsDialog)

    action = ae_with_project.menuActions["GIS"][1]
    assert action.text() == "Stacked Bandwidth", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_scenario_comparison_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.gis import CompareScenariosDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, CompareScenariosDialog)

    action = ae_with_project.menuActions["GIS"][2]
    assert action.text() == "Scenario Comparison", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_lowest_common_denominator_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.gis import LeastCommonDenominatorDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LeastCommonDenominatorDialog)

    action = ae_with_project.menuActions["GIS"][3]
    assert action.text() == "Lowest common denominator", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_simple_tag_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.gis import SimpleTagDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, SimpleTagDialog)

    action = ae_with_project.menuActions["GIS"][4]
    assert action.text() == "Simple tag", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


@pytest.mark.skip(reason="find a way to capture and close the open QFileDialog")
def test_utils_display_matrices_and_datasets_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.matrix_procedures import DisplayAequilibraEFormatsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, DisplayAequilibraEFormatsDialog)

    action = ae_with_project.menuActions["Utils"][0]
    assert action.text() == "Display Matrices and datasets", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


@pytest.mark.skip(reason="This fails because of path issue, skipping meanwhile")
def test_about_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.common_tools import AboutDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, AboutDialog)

    button = ae_with_project.menuActions["AequilibraE"][0]
    assert button.text() == "About", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    button.click()

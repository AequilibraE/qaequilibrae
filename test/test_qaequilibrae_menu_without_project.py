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


def test_open_project_menu(ae, qtbot):
    """Testing open project menu
    TODO: find a way to capture and close the open QFileDialog"""
    # def handle_trigger():
    #     check_if_new_active_window_matches_class(qtbot, QFileDialog)
    action = ae.menuActions["Project"][0]
    assert action.text() == "Open Project", "Wrong text content"
    # QTimer.singleShot(10, handle_trigger)
    # action.trigger()


def test_create_project_from_osm_menu(ae, qtbot):
    from qaequilibrae.modules.project_procedures import ProjectFromOSMDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, ProjectFromOSMDialog)

    action = ae.menuActions["Project"][1]
    assert action.text() == "Create project from OSM", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_create_project_from_layers_menu(ae, qtbot):
    from qaequilibrae.modules.project_procedures import CreatesTranspoNetDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, CreatesTranspoNetDialog)

    action = ae.menuActions["Project"][2]
    assert action.text() == "Create Project from layers", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_add_zoning_data_menu(ae, qtbot):
    action = ae.menuActions["Project"][3]
    assert action.text() == "Add zoning data", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_parameters_menu(ae, qtbot):
    action = ae.menuActions["Project"][4]
    assert action.text() == "Parameters", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_logfile_menu(ae, qtbot):
    action = ae.menuActions["Project"][5]
    assert action.text() == "logfile", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_network_preparation_menu(ae, qtbot):
    from qaequilibrae.modules.network import NetworkPreparationDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, NetworkPreparationDialog)

    action = ae.menuActions["Network Manipulation"][0]
    assert action.text() == "Network Preparation", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_add_centroid_connectors_menu(ae, qtbot):
    action = ae.menuActions["Network Manipulation"][1]
    assert action.text() == "Add centroid connectors", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_display_project_data_menu(ae, qtbot):
    action = ae.menuActions["Data"][0]
    assert action.text() == "Display project data", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_import_matrices_menu(ae, qtbot):
    from qaequilibrae.modules.matrix_procedures import LoadMatrixDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LoadMatrixDialog)

    action = ae.menuActions["Data"][1]
    assert action.text() == "Import matrices", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_trip_distribution_menu(ae, qtbot):
    from qaequilibrae.modules.distribution_procedures import DistributionModelsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, DistributionModelsDialog)

    action = ae.menuActions["Trip Distribution"][0]
    assert action.text() == "Trip Distribution", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_shortest_path_menu(ae, qtbot):
    action = ae.menuActions["Paths and assignment"][0]
    assert action.text() == "Shortest path", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_impedance_matrix_menu(ae, qtbot):
    action = ae.menuActions["Paths and assignment"][1]
    assert action.text() == "Impedance matrix", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_traffic_assignment_menu(ae, qtbot):
    action = ae.menuActions["Paths and assignment"][2]
    assert action.text() == "Traffic Assignment", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_travelling_salesman_problem_menu(ae, qtbot):
    action = ae.menuActions["Routing"][0]
    assert action.text() == "Travelling Salesman Problem", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_gis_desire_lines_menu(ae, qtbot):
    from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, DesireLinesDialog)

    action = ae.menuActions["GIS"][0]
    assert action.text() == "Desire Lines", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_gis_stacked_bandwidth_menu(ae, qtbot):
    from qaequilibrae.modules.gis import CreateBandwidthsDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, CreateBandwidthsDialog)

    action = ae.menuActions["GIS"][1]
    assert action.text() == "Stacked Bandwidth", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_gis_scenario_comparison_menu(ae, qtbot):
    action = ae.menuActions["GIS"][2]
    assert action.text() == "Scenario Comparison", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[3][0] == "Error:You need to load a project first", "Level 3 error message is missing"


def test_gis_lowest_common_denominator_menu(ae, qtbot):
    from qaequilibrae.modules.gis import LeastCommonDenominatorDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LeastCommonDenominatorDialog)

    action = ae.menuActions["GIS"][3]
    assert action.text() == "Lowest common denominator", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_gis_simple_tag_menu(ae, qtbot):
    from qaequilibrae.modules.gis import SimpleTagDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, SimpleTagDialog)

    action = ae.menuActions["GIS"][4]
    assert action.text() == "Simple tag", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_utils_display_matrices_and_datasets_menu(ae, qtbot):
    """TODO: find a way to capture and close the open QFileDialog"""
    action = ae.menuActions["Utils"][0]
    assert action.text() == "Display Matrices and datasets", "Wrong text content"


@pytest.mark.skip(reason="This fails because of path issue, skipping meanwhile")
def test_about_menu(ae, qtbot):
    from qaequilibrae.modules.common_tools import AboutDialog

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, AboutDialog)

    button = ae.menuActions["AequilibraE"][0]
    assert button.text() == "About", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    button.click()


def test_help_menu(ae, qtbot):
    """TODO: find a way to capture the opening of webpage"""
    button = ae.menuActions["AequilibraE"][1]
    assert button.text() == "Help", "Wrong text content"

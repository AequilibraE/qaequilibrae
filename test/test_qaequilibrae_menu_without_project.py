from contextlib import contextmanager

import pytest
import sys
from qgis.PyQt.QtCore import QEvent, QMetaObject, QObject, Qt
from qgis.PyQt.QtWidgets import QApplication


pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Running on Windows")


class DialogEventFilter(QObject):
    def __init__(self, dialog_class):
        super().__init__()
        self.dialog_class = dialog_class
        self.dialog = None

    def eventFilter(self, watched, event):
        if self.dialog is None and event.type() == QEvent.Type.Show and isinstance(watched, self.dialog_class):
            self.dialog = watched
            QMetaObject.invokeMethod(watched, "accept", Qt.ConnectionType.QueuedConnection)
        return super().eventFilter(watched, event)


@contextmanager
def close_dialog_in_event_loop(dialog_class):
    dialog_filter = DialogEventFilter(dialog_class)
    application = QApplication.instance()
    application.installEventFilter(dialog_filter)
    try:
        yield dialog_filter
    finally:
        application.removeEventFilter(dialog_filter)


def trigger_dialog_action(action, dialog_class):
    with close_dialog_in_event_loop(dialog_class) as dialog_filter:
        action.trigger()

    assert isinstance(dialog_filter.dialog, dialog_class), "Dialog does not have the correct class"
    assert dialog_filter.dialog.isVisible() is False, "Dialog did not close properly"


def test_open_project_menu(ae):
    """Testing open project menu
    TODO: find a way to capture and close the open QFileDialog"""
    action = ae.menuActions["Project"][0]
    assert action.text() == "Open project", "Wrong text content"
    # action.trigger()


def test_run_module_menu(ae):
    action = next((a for a in ae.menuActions["Project"] if a.text() == "Run procedures"), None)
    assert action is not None, "Menu action 'Run procedures' not found"
    assert action.text() == "Run procedures", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_scenarios_menu(ae):
    action = next((a for a in ae.menuActions["Project"] if a.text() == "Scenarios"), None)
    assert action is not None, "Menu action 'Scenarios' not found"
    assert action.text() == "Scenarios", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_trip_distribution_menu(ae):
    action = ae.menuActions["Trip distribution"][0]
    assert action.text() == "Trip distribution", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_shortest_path_menu(ae):
    action = ae.menuActions["Path computation"][0]
    assert action.text() == "Shortest path", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_impedance_matrix_menu(ae):
    action = ae.menuActions["Path computation"][1]
    assert action.text() == "Impedance matrix", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_skim_viewer_menu(ae):
    action = ae.menuActions["Path computation"][2]
    assert action.text() == "Skim viewer", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_traffic_assignment_menu(ae):
    action = ae.menuActions["Traffic assignment"][0]
    assert action.text() == "Traffic assignment", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_route_choice_menu(ae):
    action = ae.menuActions["Route choice"][0]
    assert action.text() == "Route choice", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_gis_desire_lines_menu(ae):
    from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog

    action = ae.menuActions["Mapping"][1]
    assert action.text() == "Desire lines", "Wrong text content"
    trigger_dialog_action(action, DesireLinesDialog)


def test_gis_stacked_bandwidth_menu(ae):
    from qaequilibrae.modules.gis import CreateBandwidthsDialog

    action = ae.menuActions["Mapping"][2]
    assert action.text() == "Stacked bandwidth", "Wrong text content"
    trigger_dialog_action(action, CreateBandwidthsDialog)


def test_gis_scenario_comparison_menu(ae):
    action = ae.menuActions["Mapping"][3]
    assert action.text() == "Scenario comparison", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_help_menu(ae):
    """TODO: find a way to capture the opening of webpage"""
    button = ae.menuActions["AequilibraE"][0]
    assert button.text() == "Help", "Wrong text content"


def test_gtfs_importer(ae):
    action = ae.menuActions["Transit"][0]
    assert action.text() == "Import GTFS", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_pt_skim_and_assign(ae):
    action = ae.menuActions["Transit"][1]
    assert action.text() == "Skimming and assignment", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"


def test_gtfs_explorer(ae):
    action = ae.menuActions["Transit"][2]
    assert action.text() == "Explore transit", "Wrong text content"
    action.trigger()
    messagebar = ae.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to load a project", "Level 2 error message is missing"

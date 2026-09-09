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


def test_load_project(ae_with_project):
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)
    assert ae_with_project.project is not None, "project should be loaded"


def test_run_module_menu(coquimbo_project):
    from qaequilibrae.modules.project_procedures import RunModuleDialog

    action = coquimbo_project.menuActions["Project"][1]
    assert action.text() == "Run procedures", "Wrong text content"
    trigger_dialog_action(action, RunModuleDialog)
    messagebar = coquimbo_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_scenarios_menu(ae_with_project):
    from qaequilibrae.modules.project_procedures import CreateScenariosDialog

    action = ae_with_project.menuActions["Project"][2]
    assert action.text() == "Scenarios", "Wrong text content"
    trigger_dialog_action(action, CreateScenariosDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_trip_distribution_menu(ae_with_project):
    from qaequilibrae.modules.distribution_procedures import DistributionModelsDialog

    action = ae_with_project.menuActions["Trip distribution"][0]
    assert action.text() == "Trip distribution", "Wrong text content"
    trigger_dialog_action(action, DistributionModelsDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_shortest_path_menu(ae_with_project):
    from qaequilibrae.modules.paths_procedures.show_shortest_path_dialog import ShortestPathDialog

    action = ae_with_project.menuActions["Path computation"][0]
    assert action.text() == "Shortest path", "Wrong text content"
    trigger_dialog_action(action, ShortestPathDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_impedance_matrix_menu(ae_with_project):
    from qaequilibrae.modules.paths_procedures.impedance_matrix_dialog import ImpedanceMatrixDialog

    action = ae_with_project.menuActions["Path computation"][1]
    assert action.text() == "Impedance matrix", "Wrong text content"
    trigger_dialog_action(action, ImpedanceMatrixDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_skim_viewer_menu(ae_with_project):
    from qaequilibrae.modules.paths_procedures.skim_viewer_dialog import SkimViewerDialog

    action = ae_with_project.menuActions["Path computation"][2]
    assert action.text() == "Skim viewer", "Wrong text content"
    trigger_dialog_action(action, SkimViewerDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert messagebar.messages[2][0] == "Input error:Please set an active layer to proceed", (
        "Level 2 error message is missing"
    )


def test_traffic_assignment_menu(ae_with_project):
    from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog

    action = ae_with_project.menuActions["Traffic assignment"][0]
    assert action.text() == "Traffic assignment", "Wrong text content"
    trigger_dialog_action(action, TrafficAssignmentDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_route_choice_menu(ae_with_project):
    from qaequilibrae.modules.paths_procedures.route_choice_dialog import RouteChoiceDialog

    action = ae_with_project.menuActions["Route choice"][0]
    assert action.text() == "Route choice", "Wrong text content"
    trigger_dialog_action(action, RouteChoiceDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_display_project_data_menu(ae_with_project):
    from qaequilibrae.modules.matrix_procedures import LoadProjectDataDialog

    action = ae_with_project.menuActions["Mapping"][0]
    assert action.text() == "Visualize data", "Wrong text content"
    trigger_dialog_action(action, LoadProjectDataDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_desire_lines_menu(ae_with_project):
    from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog

    action = ae_with_project.menuActions["Mapping"][1]
    assert action.text() == "Desire lines", "Wrong text content"
    trigger_dialog_action(action, DesireLinesDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_stacked_bandwidth_menu(ae_with_project):
    from qaequilibrae.modules.gis import CreateBandwidthsDialog

    action = ae_with_project.menuActions["Mapping"][2]
    assert action.text() == "Stacked bandwidth", "Wrong text content"
    trigger_dialog_action(action, CreateBandwidthsDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_scenario_comparison_menu(ae_with_project):
    from qaequilibrae.modules.gis import CompareScenariosDialog

    action = ae_with_project.menuActions["Mapping"][3]
    assert action.text() == "Scenario comparison", "Wrong text content"
    trigger_dialog_action(action, CompareScenariosDialog)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gtfs_importer(ae_with_project):
    from qaequilibrae.modules.transit_procedures.gtfs_importer import GTFSImporter

    action = ae_with_project.menuActions["Transit"][0]
    assert action.text() == "Import GTFS", "Wrong text content"
    trigger_dialog_action(action, GTFSImporter)
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gtfs_explorer(sf_project):
    action = sf_project.menuActions["Transit"][2]
    assert action.text() == "Explore transit", "Wrong text content"
    action.trigger()
    messagebar = sf_project.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to import a GTFS feed", "Level 2 error message is missing"

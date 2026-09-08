import pytest
import sys


pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Running on Windows")


def mock_dialog_exec(mocker, dialog_class):
    def handle_exec(dialog):
        assert isinstance(dialog, dialog_class), "Dialog does not have the correct class"
        dialog.close()

    mocker.patch.object(dialog_class, "exec", autospec=True, side_effect=handle_exec)


def test_load_project(ae_with_project):
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)
    assert ae_with_project.project is not None, "project should be loaded"


def test_run_module_menu(coquimbo_project, mocker):
    from qaequilibrae.modules.project_procedures import RunModuleDialog

    action = coquimbo_project.menuActions["Project"][1]
    assert action.text() == "Run procedures", "Wrong text content"
    mock_dialog_exec(mocker, RunModuleDialog)
    action.trigger()
    messagebar = coquimbo_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_scenarios_menu(ae_with_project, mocker):
    from qaequilibrae.modules.project_procedures import CreateScenariosDialog

    action = ae_with_project.menuActions["Project"][2]
    assert action.text() == "Scenarios", "Wrong text content"
    mock_dialog_exec(mocker, CreateScenariosDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_trip_distribution_menu(ae_with_project, mocker):
    from qaequilibrae.modules.distribution_procedures import DistributionModelsDialog

    action = ae_with_project.menuActions["Trip distribution"][0]
    assert action.text() == "Trip distribution", "Wrong text content"
    mock_dialog_exec(mocker, DistributionModelsDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_shortest_path_menu(ae_with_project, mocker):
    from qaequilibrae.modules.paths_procedures.show_shortest_path_dialog import ShortestPathDialog

    action = ae_with_project.menuActions["Path computation"][0]
    assert action.text() == "Shortest path", "Wrong text content"
    mock_dialog_exec(mocker, ShortestPathDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_impedance_matrix_menu(ae_with_project, mocker):
    from qaequilibrae.modules.paths_procedures.impedance_matrix_dialog import ImpedanceMatrixDialog

    action = ae_with_project.menuActions["Path computation"][1]
    assert action.text() == "Impedance matrix", "Wrong text content"
    mock_dialog_exec(mocker, ImpedanceMatrixDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_skim_viewer_menu(ae_with_project, mocker):
    from qaequilibrae.modules.paths_procedures.skim_viewer_dialog import SkimViewerDialog

    action = ae_with_project.menuActions["Path computation"][2]
    assert action.text() == "Skim viewer", "Wrong text content"
    mock_dialog_exec(mocker, SkimViewerDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert messagebar.messages[2][0] == "Input error:Please set an active layer to proceed", (
        "Level 2 error message is missing"
    )


def test_traffic_assignment_menu(ae_with_project, mocker):
    from qaequilibrae.modules.paths_procedures.traffic_assignment_dialog import TrafficAssignmentDialog

    action = ae_with_project.menuActions["Traffic assignment"][0]
    assert action.text() == "Traffic assignment", "Wrong text content"
    mock_dialog_exec(mocker, TrafficAssignmentDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_route_choice_menu(ae_with_project, mocker):
    from qaequilibrae.modules.paths_procedures.route_choice_dialog import RouteChoiceDialog

    action = ae_with_project.menuActions["Route choice"][0]
    assert action.text() == "Route choice", "Wrong text content"
    mock_dialog_exec(mocker, RouteChoiceDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_display_project_data_menu(ae_with_project, mocker):
    from qaequilibrae.modules.matrix_procedures import LoadProjectDataDialog

    action = ae_with_project.menuActions["Mapping"][0]
    assert action.text() == "Visualize data", "Wrong text content"
    mock_dialog_exec(mocker, LoadProjectDataDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_desire_lines_menu(ae_with_project, mocker):
    from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog

    action = ae_with_project.menuActions["Mapping"][1]
    assert action.text() == "Desire lines", "Wrong text content"
    mock_dialog_exec(mocker, DesireLinesDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_stacked_bandwidth_menu(ae_with_project, mocker):
    from qaequilibrae.modules.gis import CreateBandwidthsDialog

    action = ae_with_project.menuActions["Mapping"][2]
    assert action.text() == "Stacked bandwidth", "Wrong text content"
    mock_dialog_exec(mocker, CreateBandwidthsDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gis_scenario_comparison_menu(ae_with_project, mocker):
    from qaequilibrae.modules.gis import CompareScenariosDialog

    action = ae_with_project.menuActions["Mapping"][3]
    assert action.text() == "Scenario comparison", "Wrong text content"
    mock_dialog_exec(mocker, CompareScenariosDialog)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gtfs_importer(ae_with_project, mocker):
    from qaequilibrae.modules.transit_procedures.gtfs_importer import GTFSImporter

    action = ae_with_project.menuActions["Transit"][0]
    assert action.text() == "Import GTFS", "Wrong text content"
    mock_dialog_exec(mocker, GTFSImporter)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[2]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_gtfs_explorer(sf_project):
    action = sf_project.menuActions["Transit"][2]
    assert action.text() == "Explore transit", "Wrong text content"
    action.trigger()
    messagebar = sf_project.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:You need to import a GTFS feed", "Level 2 error message is missing"

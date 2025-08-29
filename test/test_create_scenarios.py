from qgis.PyQt.QtCore import Qt

from qaequilibrae.modules.project_procedures import CreateScenariosDialog


def test_create_empty_scenario(sf_project, qtbot):
    dialog = CreateScenariosDialog(sf_project)

    qtbot.mouseClick(dialog.rdo_create, Qt.LeftButton)

    dialog.txt_name.setText("test_empty_scenario")
    dialog.txt_desc.setText("Empty scenario created for test")

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    # Check if dialog was closed
    assert not dialog.isVisible()

    scenarios = sf_project.project.list_scenarios().iloc[1]
    assert scenarios["scenario_name"] == "test_empty_scenario"
    assert scenarios["description"] == "Empty scenario created for test"


def test_clone_scenario(sf_project, qtbot):
    dialog = CreateScenariosDialog(sf_project)

    dialog.txt_name.setText("test_clone_root_scenario")
    dialog.txt_desc.setText("Clone 'root' scenario for test")

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    # Check if dialog was closed
    assert not dialog.isVisible()

    scenarios = sf_project.project.list_scenarios().iloc[1]
    assert scenarios["scenario_name"] == "test_clone_root_scenario"
    assert scenarios["description"] == "Clone 'root' scenario for test"


def test_clone_scenario_from_another(sf_project, qtbot):
    # Let's create and edit a scenario to be different than 'root' we'll test
    # if it was properly cloned.
    project = sf_project.project
    project.clone_scenario("disconnect_nodes", "Disconnect nodes 7, 11 and 18 from network")
    project.use_scenario("disconnect_nodes")
    project_links = project.network.links
    for link in [10, 17, 18, 20, 27, 31, 32, 33, 34, 36, 40, 50, 54, 55, 56, 60]:
        project_links.delete(link)
    project_links.save()
    project_links.refresh()
    project.use_scenario("root")

    # Add the new scenario to the cob_scenarios
    if sf_project.project.list_scenarios().shape[0] == 2:
        sf_project.available_scenarios.extend(["disconnect_nodes"])

    dialog = CreateScenariosDialog(sf_project)

    dialog.cob_scenarios.setCurrentIndex(1)
    dialog.txt_name.setText("clone_disconnect_nodes_scenario")
    dialog.txt_desc.setText("Clone 'clone_disconnect_nodes_scenario' scenario for test")

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    # Check if dialog was closed
    assert not dialog.isVisible()

    scenarios = sf_project.project.list_scenarios().iloc[2]
    assert scenarios["scenario_name"] == "clone_disconnect_nodes_scenario"
    assert scenarios["description"] == "Clone 'clone_disconnect_nodes_scenario' scenario for test"

    project.use_scenario("clone_disconnect_nodes_scenario")
    project_links = project.network.links
    assert project_links.data.shape[0] == 60


# TODO: test run procedures in 'root' and in a scenario

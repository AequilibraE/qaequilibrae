from pathlib import Path

from qaequilibrae.modules.menu_actions.load_project_action import _project_root, _run_load_project_from_path


def test_base_path_is_root_while_scenario_is_active(sf_project):
    """With a scenario active, layer storage still resolves to the project root, not the scenario folder."""
    root = Path(sf_project.project.project_base_path)

    sf_project.project.clone_scenario("a_scenario", "Scenario for test")
    sf_project.project.use_scenario("a_scenario")

    assert Path(sf_project.project.project_base_path) == root / "scenarios" / "a_scenario"
    assert Path(sf_project._project_base_path()) == root
    assert Path(sf_project._project_layers_database()) == root / "qgis_layers.sqlite"

    sf_project.project.use_scenario("root")


def test_project_root_maps_scenario_folder_back(sf_project, tmp_path):
    """A scenario folder maps back to its root, while an unrelated 'scenarios' path is left alone."""
    root = Path(sf_project.project.project_base_path)
    sf_project.project.clone_scenario("a_scenario", "Scenario for test")

    assert _project_root(str(root / "scenarios" / "a_scenario")) == str(root)
    assert _project_root(str(root)) == str(root)

    # A folder that merely sits under a directory called "scenarios" is left alone
    stray = tmp_path / "scenarios" / "not_a_scenario"
    stray.mkdir(parents=True)
    assert _project_root(str(stray)) == str(stray)


def test_load_project_from_scenario_folder(qgis_iface, sf_project):
    """QGIS projects saved before the fix stored the scenario folder, and must still open."""
    from qaequilibrae.qaequilibrae import AequilibraEMenu

    root = Path(sf_project.project.project_base_path)
    sf_project.project.clone_scenario("a_scenario", "Scenario for test")

    ae = AequilibraEMenu(qgis_iface)
    try:
        _run_load_project_from_path(ae, str(root / "scenarios" / "a_scenario"))

        assert Path(ae.project.project_base_path) == root
        assert ae.available_scenarios == ["root", "a_scenario"]
    finally:
        ae.run_close_project()

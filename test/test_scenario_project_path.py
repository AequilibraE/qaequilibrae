from pathlib import Path

from qaequilibrae.modules.menu_actions.load_project_action import _project_root, _run_load_project_from_path


def test_failed_load_does_not_claim_project_is_open(ae, tmp_path, sioux_falls_project_path):
    _run_load_project_from_path(ae, str(tmp_path / "missing"))

    assert ae.project is None

    # The failed attempt must not prevent the user from opening a valid project next.
    try:
        _run_load_project_from_path(ae, sioux_falls_project_path)
        assert ae.project is not None
    finally:
        ae.run_close_project()


def test_base_path_is_root_while_scenario_is_active(sf_project):
    root = Path(sf_project.project.project_base_path)

    sf_project.project.clone_scenario("a_scenario", "Scenario for test")
    sf_project.project.use_scenario("a_scenario")

    assert Path(sf_project.project.project_base_path) == root / "scenarios" / "a_scenario"
    assert Path(sf_project._project_base_path()) == root
    assert Path(sf_project._project_layers_database()) == root / "qgis_layers.sqlite"

    sf_project.project.use_scenario("root")


def test_project_root_maps_scenario_folder_back(sf_project, tmp_path):
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

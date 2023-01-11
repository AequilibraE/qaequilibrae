import pytest

from aequilibrae_menu import AequilibraEMenu


@pytest.fixture(scope="function")
def ae(qgis_iface) -> AequilibraEMenu:
    return AequilibraEMenu(qgis_iface)


@pytest.fixture(scope="function")
def ae_with_project(qgis_iface) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from QAequilibraE.modules.menu_actions.load_project_action import _run_load_project_from_path

    _run_load_project_from_path(ae, "test/data/SiouxFalls_project")
    yield ae
    ae.run_close_project()

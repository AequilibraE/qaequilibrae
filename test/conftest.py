import pytest

from aequilibrae_menu import AequilibraEMenu


@pytest.fixture(scope="function")
def ae(qgis_iface) -> AequilibraEMenu:
    return AequilibraEMenu(qgis_iface)

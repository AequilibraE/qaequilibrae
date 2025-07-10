from os.path import join
from shutil import copytree
from uuid import uuid4

import pytest
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject

from qaequilibrae.modules.common_tools import ReportDialog
from qaequilibrae.qaequilibrae import AequilibraEMenu


@pytest.fixture
def folder_path(tmp_path):
    return join(tmp_path, uuid4().hex)


@pytest.fixture(scope="function")
def timeoutDetector(qgis_iface) -> None:
    def handle_trigger():
        # Check if a report window has openned
        window = QApplication.activeWindow()
        if isinstance(window, ReportDialog):
            window.close()
            raise Exception("Test timed out because of a report dialog showing")
        else:
            if window:
                window.close()
            raise Exception("Test timed out")

    timer = QTimer()
    timer.timeout.connect(handle_trigger)
    timer.setSingleShot(True)
    timer.start(3000)
    yield timer
    timer.stop()


@pytest.fixture(scope="function")
def ae(qgis_iface) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    yield ae
    qgis_iface.messageBar().messages = {0: [], 1: [], 2: [], 3: []}
    QgsProject.instance().removeAllMapLayers()


@pytest.fixture(scope="function")
def ae_with_project(qgis_iface, folder_path) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    copytree("test/data/SiouxFalls_project", folder_path)
    _run_load_project_from_path(ae, folder_path)
    yield ae
    ae.run_close_project()
    qgis_iface.messageBar().messages = {0: [], 1: [], 2: [], 3: []}
    QgsProject.instance().removeAllMapLayers()


@pytest.fixture(scope="function")
def pt_project(qgis_iface, folder_path) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    copytree("test/data/coquimbo_project", folder_path)
    _run_load_project_from_path(ae, folder_path)
    yield ae
    ae.run_close_project()
    qgis_iface.messageBar().messages = {0: [], 1: [], 2: [], 3: []}
    QgsProject.instance().removeAllMapLayers()


@pytest.fixture(scope="function")
def pt_no_feed(qgis_iface, folder_path) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    copytree("test/data/no_pt_feed", folder_path)
    _run_load_project_from_path(ae, folder_path)
    yield ae
    ae.run_close_project()
    qgis_iface.messageBar().messages = {0: [], 1: [], 2: [], 3: []}
    QgsProject.instance().removeAllMapLayers()


@pytest.fixture
def coquimbo_project(qgis_iface, folder_path) -> AequilibraEMenu:
    from aequilibrae.utils.create_example import create_example

    project = create_example(folder_path, "coquimbo")
    project.close()

    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    _run_load_project_from_path(ae, folder_path)
    yield ae
    ae.run_close_project()
    qgis_iface.messageBar().messages = {0: [], 1: [], 2: [], 3: []}
    QgsProject.instance().removeAllMapLayers()


@pytest.fixture
def sf_project(qgis_iface, folder_path) -> AequilibraEMenu:
    from aequilibrae.utils.create_example import create_example

    project = create_example(folder_path)
    project.close()

    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    _run_load_project_from_path(ae, folder_path)
    yield ae
    ae.run_close_project()
    qgis_iface.messageBar().messages = {0: [], 1: [], 2: [], 3: []}
    QgsProject.instance().removeAllMapLayers()

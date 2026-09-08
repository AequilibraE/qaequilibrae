import sys
from os.path import dirname, join
from shutil import copytree
from uuid import uuid4

import pytest
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsProject

# AequilibraE and the other dependencies are vendored in qaequilibrae/packages, and only qaequilibrae.py
# puts that folder on sys.path - which these tests never reach, because they import plugin modules
# directly. Relying on the runner to export PYTHONPATH instead is what left Windows CI unable to import
# AequilibraE at all. Appended rather than inserted, so an installed AequilibraE still takes precedence.
sys.path.append(join(dirname(dirname(__file__)), "qaequilibrae", "packages"))

from qaequilibrae.modules.common_tools import ReportDialog  # noqa: E402
from qaequilibrae.qaequilibrae import AequilibraEMenu  # noqa: E402


@pytest.fixture
def folder_path(tmp_path):
    return join(tmp_path, uuid4().hex)


@pytest.fixture(scope="function")
def timeoutDetector(qgis_iface) -> None:
    # Raising from here would cross a Qt slot boundary, and PyQt turns an unhandled exception
    # in a slot into qFatal() - an aborted process rather than a failed test. Record the reason
    # and let teardown fail the test normally.
    timed_out = []

    def handle_trigger():
        # Check if a report window has openned
        window = QApplication.activeWindow()
        # The timer measures elapsed time, not blockage, and only gets delivered once something
        # processes events - which pytest-qt does on teardown. With nothing on screen by then,
        # no dialog ever held the test up and it was simply slower than the timer: not a timeout.
        # A dialog that does block still spins an event loop, so the timer fires while it is up
        if window is None:
            return
        window.close()
        if isinstance(window, ReportDialog):
            timed_out.append("Test timed out because of a report dialog showing")
        else:
            timed_out.append("Test timed out")

    timer = QTimer()
    timer.timeout.connect(handle_trigger)
    timer.setSingleShot(True)
    timer.start(3000)
    yield timer
    timer.stop()

    if timed_out:
        pytest.fail(timed_out[0])


# Every dialog in the plugin is opened with a blocking exec(). If a test triggers one and
# nothing closes it, exec() never returns and the run hangs until the CI job is killed, with
# no indication of where it stopped. The timer below only ever fires while an event loop is
# running - which is precisely the blocked case - so closing the window there lets exec()
# return and the test fails on its own assertions instead of hanging.
# Generous on purpose: a test doing slow work inside a modal progress dialog must finish on
# its own. Lower this only if no legitimate test holds a dialog open that long.
DIALOG_WATCHDOG_MS = 60000


@pytest.fixture(scope="function", autouse=True)
def dialog_watchdog(qgis_iface):
    closed = []

    def close_stray_window():
        window = QApplication.activeModalWidget() or QApplication.activeWindow()
        if window is None:
            return
        closed.append(type(window).__name__)
        window.close()
        # A dialog is free to ignore closeEvent, so fall back to ending its event loop directly
        if window.isVisible() and hasattr(window, "done"):
            window.done(0)

    timer = QTimer()
    timer.timeout.connect(close_stray_window)
    timer.start(DIALOG_WATCHDOG_MS)
    yield timer
    timer.stop()

    if closed:
        pytest.fail(
            f"Blocked for {DIALOG_WATCHDOG_MS // 1000}s on a dialog nothing closed, so the "
            f"watchdog closed it: {', '.join(closed)}"
        )


@pytest.fixture(scope="function")
def ae(qgis_iface) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    yield ae
    qgis_iface.messageBar().messages = {0: [], 1: [], 2: [], 3: []}
    QgsProject.instance().removeAllMapLayers()


@pytest.fixture(scope="function")
def sioux_falls_project_path(folder_path):
    copytree("test/data/SiouxFalls_project", folder_path)
    return folder_path


@pytest.fixture(scope="function")
def ae_with_project(qgis_iface, sioux_falls_project_path) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    _run_load_project_from_path(ae, sioux_falls_project_path)
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

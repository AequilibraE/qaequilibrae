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


def _reset_qgis_state(qgis_iface):
    qgis_iface.messageBar().messages = {0: [], 1: [], 2: [], 3: []}
    QgsProject.instance().removeAllMapLayers()


@pytest.fixture
def menu_factory(qgis_iface):
    """Create menus and close all projects opened by a test when it finishes."""
    menus = []

    def create(project_path=None):
        ae = AequilibraEMenu(qgis_iface)
        menus.append(ae)

        if project_path is not None:
            from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

            _run_load_project_from_path(ae, project_path)

        return ae

    yield create

    for ae in menus:
        if ae.project is not None:
            ae.run_close_project()
    _reset_qgis_state(qgis_iface)


@pytest.fixture
def ae(menu_factory) -> AequilibraEMenu:
    return menu_factory()


@pytest.fixture(scope="session")
def example_project_templates(tmp_path_factory):
    """Build the example projects once and use them as read-only templates."""
    from aequilibrae.utils.create_example import create_example

    template_root = tmp_path_factory.mktemp("example_project_templates")
    templates = {}

    for name, place in (("sioux_falls", None), ("coquimbo", "coquimbo")):
        path = template_root / name
        project = create_example(str(path), place) if place else create_example(str(path))
        project.close()
        templates[name] = path

    return templates


@pytest.fixture
def sioux_falls_project_path(folder_path):
    copytree("test/data/SiouxFalls_project", folder_path)
    return folder_path


@pytest.fixture
def ae_with_project(menu_factory, sioux_falls_project_path) -> AequilibraEMenu:
    return menu_factory(sioux_falls_project_path)


@pytest.fixture
def pt_project(menu_factory, folder_path) -> AequilibraEMenu:
    copytree("test/data/coquimbo_project", folder_path)
    return menu_factory(folder_path)


@pytest.fixture
def pt_no_feed(menu_factory, folder_path) -> AequilibraEMenu:
    copytree("test/data/no_pt_feed", folder_path)
    return menu_factory(folder_path)


@pytest.fixture
def coquimbo_project(menu_factory, folder_path, example_project_templates) -> AequilibraEMenu:
    copytree(example_project_templates["coquimbo"], folder_path)
    return menu_factory(folder_path)


@pytest.fixture
def sf_project(menu_factory, folder_path, example_project_templates) -> AequilibraEMenu:
    copytree(example_project_templates["sioux_falls"], folder_path)
    return menu_factory(folder_path)

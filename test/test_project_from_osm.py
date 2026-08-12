from os import listdir, environ, makedirs
from os.path import join

import pytest
from aequilibrae.project import Project
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsRectangle

from qaequilibrae.modules.project_procedures.project_from_osm_dialog import ProjectFromOSMDialog

# The import runs on a worker thread, so the click only starts it
IMPORT_TIMEOUT_MS = 300000


@pytest.fixture
def patch_report_dialog(monkeypatch):
    from qaequilibrae.modules.project_procedures import project_from_osm_dialog

    class DummyReportDialog:
        def __init__(*args, **kwargs):
            pass

        def show(*args, **kwargs):
            pass

        def exec(*args, **kwargs):
            return None

    monkeypatch.setattr(project_from_osm_dialog, "ReportDialog", DummyReportDialog)


def run_import(dialog, qtbot):
    qtbot.mouseClick(dialog.but_run, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not dialog.running, timeout=IMPORT_TIMEOUT_MS)


def test_shows_the_logfile_as_it_is_written(ae, folder_path):
    dialog = ProjectFromOSMDialog(ae)
    dialog.output_path.setText(folder_path)

    # The log file only shows up when AequilibraE creates the project, so tailing starts before it exists
    dialog.start_tailing_log()
    dialog.refresh_log()
    assert dialog.log_view.toPlainText() == ""

    makedirs(folder_path)
    logfile = join(folder_path, "aequilibrae.log")

    with open(logfile, "w") as log:
        log.write("Downloading data\n")
    dialog.refresh_log()
    assert "Downloading data" in dialog.log_view.toPlainText()

    # Only what was appended since the last refresh makes it to the screen
    with open(logfile, "a") as log:
        log.write("Building Network\n")
    dialog.refresh_log()

    shown = dialog.log_view.toPlainText()
    assert shown.count("Downloading data") == 1
    assert "Building Network" in shown


@pytest.mark.skipif(not bool(environ.get("CI")), reason="Runs only in GitHub Action")
def test_choose_place(ae, qtbot, folder_path, patch_report_dialog):
    dialog = ProjectFromOSMDialog(ae)

    dialog.choose_place.setChecked(True)
    dialog.place.setText("Abrolhos Archipelago, Brazil")

    dialog.output_path.setText(folder_path)

    run_import(dialog, qtbot)

    assert dialog.error is None
    assert dialog.log_view.toPlainText().strip()

    dirname = listdir(folder_path)
    assert "project_database.sqlite" in dirname

    project = Project()
    project.open(folder_path)

    num_links = project.network.count_links()
    assert num_links > 0

    num_nodes = project.network.count_nodes()
    assert num_nodes > 0


@pytest.mark.skipif(not bool(environ.get("CI")), reason="Runs only in GitHub Action")
def test_select_canvas_area(ae, qtbot, folder_path, patch_report_dialog):
    dialog = ProjectFromOSMDialog(ae)

    # Define the extent you want to zoom to (xmin, ymin, xmax, ymax)
    # We'll still use Abrolhos Archipelago
    extent = QgsRectangle(-38.712296, -17.981662, -38.691573, -17.96017)

    dialog.iface.mapCanvas().setExtent(extent)  # Set the extent of the canvas

    dialog.iface.mapCanvas().refresh()  # Refresh the canvas to apply the change

    dialog.output_path.setText(folder_path)

    run_import(dialog, qtbot)

    assert dialog.error is None
    assert dialog.log_view.toPlainText().strip()

    dirname = listdir(folder_path)
    assert "project_database.sqlite" in dirname

    project = Project()
    project.open(folder_path)

    num_links = project.network.count_links()
    assert num_links > 0

    num_nodes = project.network.count_nodes()
    assert num_nodes > 0


@pytest.mark.skipif(not bool(environ.get("CI")), reason="Runs only in GitHub Action")
def test_place_not_found_keeps_the_dialog_open(ae, qtbot, folder_path):
    dialog = ProjectFromOSMDialog(ae)

    dialog.choose_place.setChecked(True)
    dialog.place.setText("Nowhere in particular, made up on the spot")
    dialog.output_path.setText(folder_path)

    run_import(dialog, qtbot)

    assert dialog.error is not None
    assert dialog.but_run.isEnabled()
    assert ae.project is None

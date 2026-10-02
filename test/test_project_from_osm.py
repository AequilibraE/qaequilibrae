from os import listdir, makedirs
from os.path import join
from types import SimpleNamespace

import pytest
from aequilibrae.project import Project
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsRectangle

from qaequilibrae.modules.project_procedures.project_from_osm_dialog import ProjectFromOSMDialog
from qaequilibrae.modules.project_procedures.project_from_osm_procedure import ProjectFromOSMProcedure


# The OSM integration tests below hang when the external Overpass service is slow.
IMPORT_TIMEOUT_MS = 300000


@pytest.fixture
def dialog(ae):
    """Tailing the log leaves a timer running, which would go on firing into the tests after this one"""
    dlg = ProjectFromOSMDialog(ae)
    yield dlg
    dlg.log_timer.stop()
    dlg.close()


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


class FailedImport:
    """A deterministic worker that lets dialog tests avoid the live OSM service."""

    def __init__(self, parent, output_path, bbox=None, place_name=None):
        self.output_path = output_path
        self.bbox = bbox
        self.place_name = place_name
        self.project = None
        self.report = []
        self.error = "Mocked import failure"
        self.signal = SimpleNamespace(connect=self.signal_connect)

    def start(self):
        self.callback(["finished"])

    def signal_connect(self, callback):
        self.callback = callback


def run_import(dialog, qtbot):
    qtbot.mouseClick(dialog.but_run, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not dialog.running, timeout=IMPORT_TIMEOUT_MS)


def relayed_progress(stages):
    """Feeds AequilibraE's progress into a procedure and returns what it passes on to the dialog"""
    procedure = ProjectFromOSMProcedure(None, "not used")
    relayed = []
    procedure.signal.connect(relayed.append)

    for message in stages:
        procedure.relay_progress(message)

    return relayed


def test_does_not_flood_the_dialog_with_per_link_progress(qtbot):
    # AequilibraE reports a maximum of zero for the stages it iterates a generator over, which
    # is precisely the stage reporting once per link. Every one of these crosses a thread
    # boundary as a queued signal, so relaying them all is what makes QGIS crawl
    stages = [["start", 0, "Adding network links"]]
    stages += [["update", i, f"{i}/0"] for i in range(1, 5001)]

    relayed = relayed_progress(stages)

    assert len(relayed) < 50, f"relayed {len(relayed)} of {len(stages)} progress messages"


def test_relays_the_update_that_completes_a_stage(qtbot):
    stages = [["start", 3, "Total polygons: 3"]] + [["update", i, ""] for i in [1, 2, 3]]

    relayed = relayed_progress(stages)

    # However fast the stage ran, the bar has to reach the end of it
    assert relayed[-1] == ["update", 3, ""]


def test_swallows_the_progress_finishing_only_one_stage(qtbot):
    # The downloader and the builder each report "finished", but only the procedure knows
    # when the whole import is over
    relayed = relayed_progress([["start", 1, "Downloading"], ["finished"]])

    assert relayed == [["start", 1, "Downloading"]]


def test_refuses_to_run_without_an_output_folder(dialog, qtbot):
    # AequilibraE would take an empty path for the current directory and create the project there
    qtbot.mouseClick(dialog.but_run, Qt.MouseButton.LeftButton)

    assert not dialog.running
    assert dialog.worker_thread is None
    assert not dialog.log_timer.isActive()
    assert dialog.iface.messageBar().messages[2][0] == "Error:Choose a folder to create the project in"


def test_refuses_to_run_without_a_place_name(dialog, qtbot, folder_path):
    dialog.output_path.setText(folder_path)
    dialog.choose_place.setChecked(True)

    qtbot.mouseClick(dialog.but_run, Qt.MouseButton.LeftButton)

    assert not dialog.running
    assert dialog.worker_thread is None
    assert dialog.iface.messageBar().messages[2][0] == "Error:Type the name of the place to import"


def test_shows_the_logfile_as_it_is_written(dialog, folder_path):
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


def test_status_and_progress_use_the_live_log_panel(dialog):
    assert dialog.log_view is dialog.log_panel.text
    assert dialog.progressbar is dialog.log_panel.bar
    assert dialog.progress_label is dialog.log_panel.stage_label

    dialog.signal_handler(["set_text", "Creating project"])
    assert dialog.log_panel.stage_label.text() == "Creating project"

    dialog.signal_handler(["start", 10, "Downloading network"])
    assert dialog.progressbar.maximum() == 10
    assert dialog.progressbar.value() == 0
    assert dialog.progress_label.text() == "Downloading network"

    dialog.signal_handler(["update", 4, ""])
    assert dialog.progressbar.value() == 4

    dialog.log_bridge.log_line.emit("Imported a link")
    assert "Imported a link" in dialog.log_view.toPlainText()


def test_panel_shows_the_imported_model(dialog, folder_path, patch_report_dialog):
    """The import leaves a project open, and the panel is only aware of it if it is told

    Without this the plugin reports a model as open while the panel holds no scenario and no
    layer to load, so there is no way of getting the network on the screen.
    """
    project = Project()
    project.new(folder_path)

    # Standing in for an import that has just succeeded, so the test does not hit the network
    dialog.output_path.setText(folder_path)
    dialog.worker_thread = SimpleNamespace(project=project, output_path=folder_path, report=[], error=None)

    dialog.job_finished()

    ae = dialog.qgis_project
    assert ae.project is project
    assert ae.available_scenarios == ["root"]
    assert {"links", "nodes"} <= set(ae.layers)
    assert ae.projectManager.count() == 1

    ae.run_close_project()


def test_run_passes_canvas_extent_to_importer(dialog, qtbot, folder_path, monkeypatch):
    from qaequilibrae.modules.project_procedures import project_from_osm_dialog

    monkeypatch.setattr(project_from_osm_dialog, "ProjectFromOSMProcedure", FailedImport)
    extent = QgsRectangle(-38.712296, -17.981662, -38.691573, -17.96017)
    dialog.iface.mapCanvas().setExtent(extent)
    canvas_extent = dialog.iface.mapCanvas().extent()
    dialog.output_path.setText(folder_path)

    qtbot.mouseClick(dialog.but_run, Qt.MouseButton.LeftButton)

    assert dialog.worker_thread.bbox == [
        canvas_extent.xMinimum(),
        canvas_extent.yMinimum(),
        canvas_extent.xMaximum(),
        canvas_extent.yMaximum(),
    ]
    assert dialog.worker_thread.place_name is None
    assert dialog.error == "Mocked import failure"
    assert dialog.but_run.isEnabled()


def test_run_passes_place_name_to_importer(dialog, qtbot, folder_path, monkeypatch):
    from qaequilibrae.modules.project_procedures import project_from_osm_dialog

    monkeypatch.setattr(project_from_osm_dialog, "ProjectFromOSMProcedure", FailedImport)
    dialog.choose_place.setChecked(True)
    dialog.place.setText("Abrolhos Archipelago, Brazil")
    dialog.output_path.setText(folder_path)

    qtbot.mouseClick(dialog.but_run, Qt.MouseButton.LeftButton)

    assert dialog.worker_thread.bbox is None
    assert dialog.worker_thread.place_name == "Abrolhos Archipelago, Brazil"
    assert dialog.error == "Mocked import failure"
    assert dialog.but_run.isEnabled()
    assert dialog.qgis_project.project is None


@pytest.mark.skip(reason="Temporarily disabled: depends on the external Overpass service")
def test_choose_place(dialog, qtbot, folder_path, patch_report_dialog):
    dialog.choose_place.setChecked(True)
    dialog.place.setText("Abrolhos Archipelago, Brazil")
    dialog.output_path.setText(folder_path)

    run_import(dialog, qtbot)

    assert dialog.error is None
    assert dialog.log_view.toPlainText().strip()
    assert "project_database.sqlite" in listdir(folder_path)

    project = Project()
    project.open(folder_path)
    assert project.network.count_links() > 0
    assert project.network.count_nodes() > 0


@pytest.mark.skip(reason="Temporarily disabled: depends on the external Overpass service")
def test_select_canvas_area(dialog, qtbot, folder_path, patch_report_dialog):
    extent = QgsRectangle(-38.712296, -17.981662, -38.691573, -17.96017)
    dialog.iface.mapCanvas().setExtent(extent)
    dialog.iface.mapCanvas().refresh()
    dialog.output_path.setText(folder_path)

    run_import(dialog, qtbot)

    assert dialog.error is None
    assert dialog.log_view.toPlainText().strip()
    assert "project_database.sqlite" in listdir(folder_path)

    project = Project()
    project.open(folder_path)
    assert project.network.count_links() > 0
    assert project.network.count_nodes() > 0


@pytest.mark.skip(reason="Temporarily disabled: depends on the external Overpass service")
def test_place_not_found_keeps_the_dialog_open(dialog, qtbot, folder_path):
    dialog.choose_place.setChecked(True)
    dialog.place.setText("Nowhere in particular, made up on the spot")
    dialog.output_path.setText(folder_path)

    run_import(dialog, qtbot)

    assert dialog.error is not None
    assert dialog.but_run.isEnabled()
    assert dialog.qgis_project.project is None

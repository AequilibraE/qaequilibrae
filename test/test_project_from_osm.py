from os import listdir, environ

import pytest
from aequilibrae.project import Project
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsRectangle

from qaequilibrae.modules.project_procedures.project_from_osm_dialog import ProjectFromOSMDialog


@pytest.fixture
def patch_report_dialog(monkeypatch):
    from qaequilibrae.modules.project_procedures import project_from_osm_dialog

    class DummyReportDialog:
        def __init__(*args, **kwargs):
            pass

        def show(*args, **kwargs):
            pass

        def exec_(*args, **kwargs):
            return None

    monkeypatch.setattr(project_from_osm_dialog, "ReportDialog", DummyReportDialog)


@pytest.mark.skipif(not bool(environ.get("CI")), reason="Runs only in GitHub Action")
def test_choose_place(ae, qtbot, folder_path, patch_report_dialog):
    dialog = ProjectFromOSMDialog(ae)

    dialog.choose_place.setChecked(True)
    dialog.place.setText("Abrolhos Archipelago, Brazil")

    dialog.output_path.setText(folder_path)

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

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

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    dirname = listdir(folder_path)
    assert "project_database.sqlite" in dirname

    project = Project()
    project.open(folder_path)

    num_links = project.network.count_links()
    assert num_links > 0

    num_nodes = project.network.count_nodes()
    assert num_nodes > 0

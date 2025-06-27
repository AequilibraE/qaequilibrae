import pytest
from os import listdir
from qgis.PyQt.QtCore import Qt
from aequilibrae.project import Project

from qaequilibrae.modules.project_procedures.project_from_osm_dialog import ProjectFromOSMDialog


@pytest.mark.skip("Not working")
def test_choose_place(ae, qtbot, folder_path):
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

import os
import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis, QgsVectorLayer
from qaequilibrae.modules.public_transport_procedures.gtfs_feed import GTFSFeed
from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter


def test_click(ae_with_project, qtbot):
    dialog = GTFSImporter(ae_with_project)
    dialog.show()

    assert dialog.label_3.text() == "Add Transit Table"
    assert dialog.rdo_clear.text() == "Crete New Route System"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_add, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"


@pytest.fixture
def create_feed(pt_project, transit_object):
    dialog = GTFSFeed(pt_project, transit_object)
    dialog.show()

    yield dialog


def test_set_data(create_feed):
    gtfs_path = "test/data/coquimbo_project/gtfs_coquimbo.zip"
    
    create_feed.set_data(gtfs_path)

    assert len(create_feed.feed) == 1
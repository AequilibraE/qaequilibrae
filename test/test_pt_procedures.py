import os
import pytest
from unittest import mock
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis, QgsVectorLayer
from qaequilibrae.modules.public_transport_procedures.gtfs_feed import GTFSFeed
from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter


def test_click_importer(ae_with_project, qtbot):
    dialog = GTFSImporter(ae_with_project)
    dialog.show()

    assert dialog.label_3.text() == "Add Transit Table"
    assert dialog.rdo_clear.text() == "Crete New Route System"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_execute, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"


# @mock.patch("tradesman.data_retrieval.osm_tags.import_osm_data.generic_tag")
def test_click_feed(transit_object, pt_project, qtbot):
    dialog = GTFSFeed(transit_object, pt_project)
    dialog.show()

    assert dialog.label_2.text() == "Service date"
    assert dialog.label_3.text() == "Agency*"
    assert dialog.label_4.text() == "Description*"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_add, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"

import os
import pytest
from unittest import mock
from uuid import uuid4
from PyQt5.QtCore import Qt
from qaequilibrae.modules.public_transport_procedures.gtfs_feed import GTFSFeed
from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter


def test_click_new_importer(ae_with_project, qtbot):
    dialog = GTFSImporter(ae_with_project)
    dialog.show()

    assert dialog.label_3.text() == "Add Transit Table"
    assert dialog.rdo_clear.text() == "Crete New Route System"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_execute, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"


def test_click_add_importer(pt_project, qtbot):
    dialog = GTFSImporter(pt_project)
    dialog.show()

    assert dialog.rdo_clear.text() == "Overwrite Routes"
    assert dialog.rdo_keep.text() == "Add to Existing Routes"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_execute, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"


@pytest.fixture
def pt_object(ae_with_project):
    from aequilibrae.transit import Transit
    data = Transit(ae_with_project)

    yield data

@pytest.mark.skip(reason="PT object is not working properly within the test")
def test_click_feed(pt_project, pt_object, qtbot):
    dialog = GTFSFeed(pt_project, pt_object)
    dialog.show()

    assert dialog.label_2.text() == "Service date"
    assert dialog.label_3.text() == "Agency*"
    assert dialog.label_4.text() == "Description*"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_add, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"

import os
import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis, QgsVectorLayer
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


@pytest.mark.skip(reasson="Problem with test")
def test_click_feed(pt_project, qtbot):
    from aequilibrae.transit import Transit
    
    data = Transit(pt_project.project)

    dialog = GTFSFeed(pt_project, data, True)
    dialog.show()

    assert dialog.label.text() == "Route capacities"
    assert dialog.label_2.text() == "Service date"
    assert dialog.label_3.text() == "Description*"
    assert dialog.label_4.text() == "Agency*"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_add, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"

    messagebar = pt_project.iface.messageBar()
    assert messagebar.messages[3] == "Error:Enter agency and description"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_new_row, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"

    dialog.close()


def test_pt_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter
    from test.test_qaequilibrae_menu_with_project import check_if_new_active_window_matches_class

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, GTFSImporter)

    action = ae_with_project.menuActions["Public Transport"][0]
    assert action.text() == "Public Transport", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)
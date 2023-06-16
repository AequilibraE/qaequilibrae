from os.path import isfile, join
import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis, QgsVectorLayer
from qaequilibrae.modules.public_transport_procedures.gtfs_feed import GTFSFeed
from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter


def test_click_new_importer(ae_with_project, qtbot):
    dialog = GTFSImporter(ae_with_project)
    dialog.show()

    assert dialog.label_3.text() == "Add transit table"
    assert dialog.rdo_clear.text() == "Create new route system"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_execute, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"
    
    dialog.close()


def test_click_add_importer(pt_project, qtbot):
    dialog = GTFSImporter(pt_project)
    dialog.show()

    assert dialog.rdo_clear.text() == "Overwrite Routes"
    assert dialog.rdo_keep.text() == "Add to Existing Routes"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_execute, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"

    dialog.close()


def test_click_feed(pt_project, qtbot):
    from aequilibrae.transit import Transit
    
    data = Transit(pt_project.project)

    dialog = GTFSFeed(pt_project, data, True)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    assert dialog.label.text() == "Route capacities"
    assert dialog.label_2.text() == "Service date"
    assert dialog.label_3.text() == "Description*"
    assert dialog.label_4.text() == "Agency*"

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.but_new_row, Qt.LeftButton)

    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"


def test_pt_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter
    from test.test_qaequilibrae_menu_with_project import check_if_new_active_window_matches_class

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, GTFSImporter)

    action = ae_with_project.menuActions["Public Transport"][0]
    assert action.text() == "Import GTFS", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


@pytest.mark.skip(reason="Test is not working")
def test_add_new_feed(ae_with_project):
    from aequilibrae.transit import Transit
    import sqlite3

    data = Transit(ae_with_project.project)
    feed = GTFSFeed(ae_with_project, data, True)

    gtfs_file = "test/data/coquimbo_project/gtfs_coquimbo.zip"
    feed.set_data(gtfs_file)
    
    feed.feed.gtfs_data.agency.agency = "agency name 1"
    feed.feed.gtfs_data.agency.description = "add description 1"
    feed.feed.gtfs_data.agency.feed_date = "2016-09-16"

    importer = GTFSImporter(ae_with_project)
    importer.set_feed(feed.feed)
    importer.execute_importer()


@pytest.mark.skip(reason="Test is not working")
def test_add_other_feed(pt_project):
    from aequilibrae.transit import Transit
    import sqlite3

    data = Transit(pt_project.project)
    feed = GTFSFeed(pt_project, data, True)

    gtfs_file = "test/data/coquimbo_project/gtfs_coquimbo.zip"
    feed.set_data(gtfs_file)
    
    feed.feed.gtfs_data.agency.agency = "agency name 1"
    feed.feed.gtfs_data.agency.description = "add description 1"
    feed.feed.gtfs_data.agency.feed_date = "2016-09-16"
    
    importer = GTFSImporter(pt_project)
    importer.set_feed(feed.feed)
    # importer.execute_importer()

    db_path = join(pt_project.project.project_base_path, "public_transport.sqlite")
    # Check if PT database was created
    assert isfile(db_path) is True

    assert feed.feed is not None

    feed.feed.set_allow_map_match(True)
    feed.feed.doWork()

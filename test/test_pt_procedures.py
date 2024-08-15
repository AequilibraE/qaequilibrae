import os
import sqlite3
import pytest
from datetime import datetime
from aequilibrae.transit import Transit
from PyQt5.QtCore import QTimer
from qaequilibrae.modules.public_transport_procedures.gtfs_feed import GTFSFeed
from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter


def test_pt_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter
    from test.test_qaequilibrae_menu_with_project import check_if_new_active_window_matches_class

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, GTFSImporter)

    action = ae_with_project.menuActions["Public Transport"][0]
    assert action.text() == "Import GTFS", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()


def test_add_new_feed(pt_no_feed, mocker):
    mocker.patch(
        "qaequilibrae.modules.public_transport_procedures.gtfs_feed.GTFSFeed.open_feed",
    )

    importer = GTFSImporter(pt_no_feed)
    assert importer.label_3.text() == "Add transit table"
    assert importer.rdo_clear.text() == "Create new route system"

    data = Transit(pt_no_feed.project)
    feed = GTFSFeed(pt_no_feed, data)

    assert feed.label.text() == "Route capacities"
    assert feed.label_2.text() == "Service date"
    assert feed.label_3.text() == "Description*"
    assert feed.label_4.text() == "Agency*"

    gtfs_file = "test/data/coquimbo_project/gtfs_coquimbo.zip"
    feed.set_data(gtfs_file)
    feed.led_agency.setText("New agency")
    feed.led_description.setText("Adds new agency description")
    feed.service_calendar.setSelectedDate(datetime(2016, 4, 16))
    feed.return_feed()

    importer.set_feed(feed.feed)
    importer.rdo_keep.setChecked(True)
    importer.execute_importer()

    db_path = os.path.join(pt_no_feed.project.project_base_path, "public_transport.sqlite")
    conn = sqlite3.connect(db_path)
    var = conn.execute("select count(agency_id) from agencies").fetchone()[0]

    assert var == 1


@pytest.mark.parametrize(
    ("is_checked", "set_date", "set_agency"),
    [(False, (2016, 6, 17), "New agency"), (True, (2016, 8, 21), "Other agency")],
)
def test_add_other_feed(pt_project, set_agency, set_date, is_checked, mocker):
    mocker.patch(
        "qaequilibrae.modules.public_transport_procedures.gtfs_feed.GTFSFeed.open_feed",
    )

    importer = GTFSImporter(pt_project)
    assert importer.label_3.text() == "Resetting Transit Tables"
    assert importer.rdo_clear.text() == "Overwrite Routes"
    assert importer.rdo_keep.text() == "Add to Existing Routes"

    data = Transit(pt_project.project)
    feed = GTFSFeed(pt_project, data)

    assert feed.label.text() == "Route capacities"
    assert feed.label_2.text() == "Service date"
    assert feed.label_3.text() == "Description*"
    assert feed.label_4.text() == "Agency*"

    gtfs_file = "test/data/coquimbo_project/gtfs_coquimbo.zip"
    feed.set_data(gtfs_file)
    feed.led_agency.setText(set_agency)
    feed.led_description.setText("Adds new agency description")
    feed.service_calendar.setSelectedDate(datetime(*set_date))
    feed.return_feed()

    importer.rdo_clear.setChecked(is_checked)
    if not is_checked:
        importer.rdo_keep.setChecked(True)
    importer.set_feed(feed.feed)
    importer.execute_importer()

    db_path = os.path.join(pt_project.project.project_base_path, "public_transport.sqlite")
    conn = sqlite3.connect(db_path)
    var = conn.execute("select count(agency_id) from agencies").fetchone()[0]

    if is_checked:
        assert var == 1
    else:
        assert var == 2

from datetime import datetime

import pytest
from aequilibrae.transit import Transit

from qaequilibrae.modules.transit_procedures.gtfs_feed import GTFSFeed
from qaequilibrae.modules.transit_procedures.gtfs_importer import GTFSImporter


def test_add_new_feed(pt_no_feed, mocker):
    """A GTFS feed imported into a project with no transit registers its agency."""
    mocker.patch(
        "qaequilibrae.modules.transit_procedures.gtfs_feed.GTFSFeed.open_feed",
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

    with pt_no_feed.project.transit_connection as conn:
        var = conn.execute("select count(agency_id) from agencies").fetchone()[0]

    assert var == 1


def test_gtfs_import_progress_uses_shared_bridge(pt_no_feed):
    """Progress signals from the importer drive its bar and stage label, and clear on finish."""
    importer = GTFSImporter(pt_no_feed)

    importer.signal_handler(["start", 9, "Reading GTFS"])
    assert importer.progressbar.maximum() == 9
    assert importer.progressbar.value() == 0
    assert importer.progress_label.text() == "Reading GTFS"

    importer.signal_handler(["update", 4, "Building routes"])
    assert importer.progressbar.value() == 4
    assert importer.progress_label.text() == "Building routes"

    importer.signal_handler(["set_text", "Finishing import"])
    assert importer.progress_label.text() == "Finishing import"

    importer.signal_handler(["finished"])
    assert importer.progress_label.text() == ""


@pytest.mark.parametrize(
    ("is_checked", "set_date", "set_agency"),
    [(False, (2016, 6, 17), "New agency"), (True, (2016, 8, 21), "Other agency")],
)
def test_add_other_feed(pt_project, set_agency, set_date, is_checked, mocker):
    """A second feed either replaces the existing routes or is added alongside them."""
    mocker.patch(
        "qaequilibrae.modules.transit_procedures.gtfs_feed.GTFSFeed.open_feed",
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

    with pt_project.project.transit_connection as conn:
        var = conn.execute("select count(agency_id) from agencies").fetchone()[0]

    target = 1 if is_checked else 2
    assert var == target

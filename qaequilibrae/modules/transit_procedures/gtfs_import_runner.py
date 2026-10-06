"""Import GTFS feeds into a project."""

from collections.abc import Callable, Iterable
from typing import Any

from qaequilibrae.modules.common_tools import quote_identifier

TRANSIT_TABLES_TO_CLEAR = (
    "agencies",
    "fare_attributes",
    "fare_rules",
    "fare_zones",
    "pattern_mapping",
    "route_links",
    "routes",
    "stop_connectors",
    "stops",
    "trips",
    "trips_schedule",
)


def import_gtfs_feeds(
    project: Any,
    feeds: Iterable[Any],
    *,
    overwrite: bool = False,
    signal_handler: Callable[[Any], None] | None = None,
) -> None:
    """Optionally clear previous transit records, then import feeds in order."""
    if overwrite:
        with project.transit_connection as connection:
            for table in TRANSIT_TABLES_TO_CLEAR:
                connection.execute(f"DELETE FROM {quote_identifier(table)}")

    for feed in feeds:
        if signal_handler is not None:
            feed.signal.connect(signal_handler)
        feed.execute_import()

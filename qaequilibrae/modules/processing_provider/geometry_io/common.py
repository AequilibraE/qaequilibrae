"""Read and write project geometry through QGIS."""

from typing import Any

import pandas as pd
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFields,
    QgsProcessingException,
)

from qaequilibrae.modules.common_tools.vector_layer_helpers import (
    add_dataframe_features,
    fields_from_dataframe,
    rows_from_feature_source,
)

__all__ = [
    "add_dataframe_to_sink",
    "copy_record_attributes",
    "fields_from_dataframe",
    "ignored_input_fields",
    "project_table",
    "source_rows",
]


def project_table(project, table_name):
    """Return the project table named by a geometry algorithm."""
    return project.zoning if table_name == "zones" else getattr(project.network, table_name)


def ignored_input_fields(table_name: str, identifier_field: str | None = None, *, adding: bool = False) -> set[str]:
    """Return fields managed by AequilibraE rather than a geometry input."""
    ignored = {"geometry", "ogc_fid"}
    if identifier_field:
        ignored.add(identifier_field)
    if table_name == "links":
        ignored.add("distance")
        if adding:
            ignored.update({"a_node", "b_node"})
    elif table_name == "nodes":
        ignored.update({"modes", "link_types"})
    elif table_name == "zones":
        ignored.add("area")
    return ignored


def copy_record_attributes(record, table, row, ignored_fields, *, skip_nulls: bool) -> None:
    """Copy supported input attributes to a project record."""
    record_fields = getattr(record, "data_fields", None)
    data_fields = set(record_fields() if record_fields is not None else table.fields.all_fields())
    for field, value in row.items():
        if field in ignored_fields or (skip_nulls and value is None):
            continue
        if field in data_fields:
            setattr(record, field, value)


def add_dataframe_to_sink(dataframe: pd.DataFrame, sink, fields: QgsFields, feedback) -> int:
    """Write a GeoDataFrame to a Processing feature sink."""
    try:
        return add_dataframe_features(dataframe, sink, fields, feedback)
    except RuntimeError as error:
        raise QgsProcessingException("Could not write a project feature to the output") from error


def source_rows(source) -> list[dict[str, Any]]:
    """Return lower-case attribute dictionaries and Shapely geometries."""
    return rows_from_feature_source(source, target_crs=QgsCoordinateReferenceSystem("EPSG:4326"))

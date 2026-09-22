"""QGIS adapters shared by the project geometry algorithms."""

from typing import Any

import pandas as pd
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFields,
    QgsGeometry,
    QgsProcessingException,
    QgsProject,
)

from qaequilibrae.modules.common_tools.vector_layer_helpers import (
    add_dataframe_features,
    fields_from_dataframe,
)

__all__ = ["add_dataframe_to_sink", "fields_from_dataframe", "source_rows"]


def record_data_fields(record, table) -> list[str]:
    """Return the editable fields exposed by a project record."""
    data_fields = getattr(record, "data_fields", None)
    return data_fields() if data_fields is not None else table.fields.all_fields()


def add_dataframe_to_sink(dataframe: pd.DataFrame, sink, fields: QgsFields, feedback) -> int:
    """Write a GeoDataFrame to a Processing feature sink."""
    try:
        return add_dataframe_features(dataframe, sink, fields, feedback)
    except RuntimeError as error:
        raise QgsProcessingException("Could not write a project feature to the output") from error


def source_rows(source) -> list[dict[str, Any]]:
    """Return lower-case attribute dictionaries and Shapely geometries."""
    import shapely.wkb

    names = [field.name().lower() for field in source.fields()]
    target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    source_crs = source.sourceCrs()
    coordinate_transform = None
    if source_crs.isValid() and source_crs != target_crs:
        coordinate_transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
    rows = []
    for feature in source.getFeatures():
        geometry = feature.geometry()
        if geometry is not None and not geometry.isEmpty() and coordinate_transform is not None:
            geometry = QgsGeometry(geometry)
            geometry.transform(coordinate_transform)
        rows.append(
            {
                **dict(zip(names, feature.attributes(), strict=True)),
                "geometry": None if geometry is None or geometry.isEmpty() else shapely.wkb.loads(bytes(geometry.asWkb())),
            }
        )
    return rows

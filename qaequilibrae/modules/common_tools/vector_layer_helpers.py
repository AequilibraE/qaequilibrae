"""Shared helpers for creating QGIS memory layers from tabular data."""

from typing import Any

import pandas as pd
from qgis.PyQt.QtCore import QMetaType
from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProject,
)


def fields_from_dataframe(dataframe: pd.DataFrame) -> QgsFields:
    """Build QGIS fields for the non-geometry columns in a DataFrame."""
    fields = QgsFields()
    for name in dataframe.columns:
        if name == "geometry":
            continue
        series = dataframe[name]
        if pd.api.types.is_bool_dtype(series):
            field_type = QMetaType.Type.Bool
        elif pd.api.types.is_integer_dtype(series):
            field_type = QMetaType.Type.LongLong
        elif pd.api.types.is_numeric_dtype(series):
            field_type = QMetaType.Type.Double
        else:
            field_type = QMetaType.Type.QString
        fields.append(QgsField(str(name), field_type))
    return fields


def add_dataframe_features(dataframe: pd.DataFrame, sink, fields: QgsFields, feedback=None) -> int:
    """Add DataFrame rows to a QGIS feature sink and return the row count."""
    attribute_names = [field.name() for field in fields]
    written = 0
    for _, row in dataframe.iterrows():
        if feedback is not None and feedback.isCanceled():
            break

        feature = QgsFeature(fields)
        geometry = row.get("geometry")
        if geometry is not None and not getattr(geometry, "is_empty", False):
            qgis_geometry = QgsGeometry()
            qgis_geometry.fromWkb(bytes(geometry.wkb))
            feature.setGeometry(qgis_geometry)
        feature.setAttributes([_qgis_value(row.get(name)) for name in attribute_names])

        if not sink.addFeature(feature):
            raise RuntimeError("Could not add a DataFrame row to the QGIS layer")
        written += 1
    return written


def centroid_coordinates(source, id_field_index: int, feedback) -> dict[int, tuple[float, float]]:
    """Read node or zone IDs and geometry centroids from a feature source."""
    coordinates = {}
    for feature in source.getFeatures():
        if feedback.isCanceled():
            break
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            continue
        point = geometry.centroid().asPoint()
        coordinates[int(feature.attributes()[id_field_index])] = (point.x(), point.y())
    return coordinates


def rows_from_feature_source(source, target_crs=None) -> list[dict[str, Any]]:
    """Return lower-case attributes and Shapely geometries from a QGIS source.

    Transform geometries to ``target_crs`` if supplied; otherwise preserve source coordinates.
    """
    import shapely.wkb

    names = [field.name().lower() for field in source.fields()]
    source_crs = source.sourceCrs() if hasattr(source, "sourceCrs") else source.crs()
    coordinate_transform = None
    if target_crs is not None and source_crs.isValid() and source_crs != target_crs:
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
                "geometry": None
                if geometry is None or geometry.isEmpty()
                else shapely.wkb.loads(bytes(geometry.asWkb())),
            }
        )
    return rows


def _qgis_value(value):
    """Convert scalar pandas missing values to ``None`` for QGIS attributes."""
    if value is None:
        return None
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return value
    return None if not hasattr(missing, "__len__") and missing else value

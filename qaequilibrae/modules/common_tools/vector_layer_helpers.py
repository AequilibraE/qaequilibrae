"""Shared helpers for creating QGIS memory layers from tabular data."""

import pandas as pd
from qgis.PyQt.QtCore import QMetaType
from qgis.core import QgsFeature, QgsField, QgsFields, QgsGeometry


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


def geometry_type_from_geodataframe(geodataframe) -> str:
    """Return the QGIS memory-layer geometry type for a GeoDataFrame."""
    geometry_types = set(geodataframe.geometry.geom_type.dropna())
    if geometry_types & {"Point", "MultiPoint"}:
        return "Point"
    if geometry_types & {"LineString", "MultiLineString"}:
        return "LineString"
    if geometry_types & {"Polygon", "MultiPolygon"}:
        return "Polygon"
    return "LineString"


def crs_string(geodataframe) -> str:
    """Return a CRS string accepted by a QGIS memory-layer URI."""
    if geodataframe.crs is None:
        return "EPSG:4326"
    return geodataframe.crs.to_string()


def _qgis_value(value):
    if value is None:
        return None
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return value
    return None if not hasattr(missing, "__len__") and missing else value

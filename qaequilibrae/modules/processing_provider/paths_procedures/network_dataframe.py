"""Adapters that turn QGIS feature sources into tabular routing input."""

from qgis.core import QgsFeatureSource


def network_dataframe_from_source(source: QgsFeatureSource):
    """Return source attributes as a DataFrame with case-insensitive column names.

    Geometry deliberately does not cross this boundary.  AequilibraE's graph builder
    only needs network attributes; the Processing algorithm keeps the source features
    so it can attach their geometries to the output later.
    """
    import pandas as pd

    fields = [field.name().lower() for field in source.fields()]
    return pd.DataFrame((feature.attributes() for feature in source.getFeatures()), columns=fields)

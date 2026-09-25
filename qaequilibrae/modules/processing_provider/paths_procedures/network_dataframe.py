"""Adapters that turn QGIS feature sources into tabular routing input."""

from collections.abc import Iterable
from typing import cast

from qgis.core import QgsFeature, QgsFeatureSource


def network_dataframe_from_source(source: QgsFeatureSource):
    """Return source attributes as a DataFrame with case-insensitive column names.

    Geometry deliberately does not cross this boundary.  AequilibraE's graph builder
    only needs network attributes; the Processing algorithm keeps the source features
    so it can attach their geometries to the output later.
    """
    import pandas as pd

    fields = [field.name().lower() for field in source.fields()]
    features = cast(Iterable[QgsFeature], source.getFeatures())
    return pd.DataFrame((feature.attributes() for feature in features), columns=fields)

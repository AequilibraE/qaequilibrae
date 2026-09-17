import numpy as np
import pandas as pd
from qgis.core import QgsFeatureSource


def network_dataframe_from_source(source: QgsFeatureSource) -> pd.DataFrame:
    """Read network attributes without constructing a GeoDataFrame.

    Routing does not use link geometry or a CRS. Avoiding GeoPandas here also avoids loading
    pyproj's native PROJ bindings into the QGIS process.
    """

    fields = [field.name().lower() for field in source.fields()]
    rows = [feature.attributes() for feature in source.getFeatures()]
    return pd.DataFrame(rows, columns=fields)


def make_writable_network_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Copy network columns into the dtypes and memory layout used by AequilibraE."""

    dtype_map = {
        "link_id": np.int64,
        "a_node": np.int64,
        "b_node": np.int64,
        "direction": np.int8,
    }

    data = {}
    for column in dataframe.columns:
        series = dataframe[column]
        if column in dtype_map:
            dtype = dtype_map[column]
        elif pd.api.types.is_integer_dtype(series):
            dtype = np.int64
        elif pd.api.types.is_float_dtype(series):
            dtype = np.float64
        elif pd.api.types.is_numeric_dtype(series):
            dtype = np.float64
        else:
            dtype = object

        array = np.asarray(series.tolist(), dtype=dtype)
        data[column] = np.require(array, dtype=dtype, requirements=["C", "W", "O"])

    return pd.DataFrame(data, copy=False)

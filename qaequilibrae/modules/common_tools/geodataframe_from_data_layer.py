import geopandas as gpd
from qgis.core import QgsVectorLayer

from .vector_layer_helpers import rows_from_feature_source


def geodataframe_from_layer(layer: QgsVectorLayer) -> gpd.GeoDataFrame:
    """Creates a gpd.GeoDataFrame from a data layer."""

    columns = [field.name().lower() for field in layer.fields()]
    gdf = gpd.GeoDataFrame(
        rows_from_feature_source(layer),
        columns=[*columns, "geometry"],
        geometry="geometry",
        crs=layer.crs().authid(),
    )
    gdf["geoms"] = [None if geometry is None else geometry.wkb for geometry in gdf.geometry]
    return gdf

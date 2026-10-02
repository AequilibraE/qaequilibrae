import geopandas as gpd
from qgis.core import QgsProject, QgsVectorLayer

from .vector_layer_helpers import (
    add_dataframe_features,
    crs_string,
    fields_from_dataframe,
    geometry_type_from_geodataframe,
)


def layer_from_geodataframe(gdf: gpd.GeoDataFrame, layer_name: str):
    """Transform a GeoDataFrame to a QGIS vector layer in memory."""

    geometry_type = geometry_type_from_geodataframe(gdf)
    vl = QgsVectorLayer(f"{geometry_type}?crs={crs_string(gdf)}", layer_name, "memory")
    pr = vl.dataProvider()

    fields = fields_from_dataframe(gdf)
    pr.addAttributes(list(fields))
    vl.updateFields()

    add_dataframe_features(gdf, pr, fields)

    QgsProject.instance().addMapLayer(vl)

    # returns the layer handle
    return vl

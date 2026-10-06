import geopandas as gpd
from qgis.core import QgsProject, QgsVectorLayer

from .vector_layer_helpers import add_dataframe_features, fields_from_dataframe


def layer_from_geodataframe(gdf: gpd.GeoDataFrame, layer_name: str):
    """Transform a GeoDataFrame to a QGIS vector layer in memory."""

    geometry_types = set(gdf.geometry.geom_type.dropna())
    if geometry_types & {"Point", "MultiPoint"}:
        geometry_type = "Point"
    elif geometry_types & {"LineString", "MultiLineString"}:
        geometry_type = "LineString"
    elif geometry_types & {"Polygon", "MultiPolygon"}:
        geometry_type = "Polygon"
    else:
        geometry_type = "LineString"
    crs = gdf.crs.to_string() if gdf.crs is not None else "EPSG:4326"
    vl = QgsVectorLayer(f"{geometry_type}?crs={crs}", layer_name, "memory")
    pr = vl.dataProvider()

    fields = fields_from_dataframe(gdf)
    pr.addAttributes(list(fields))
    vl.updateFields()

    add_dataframe_features(gdf, pr, fields)

    QgsProject.instance().addMapLayer(vl)

    # returns the layer handle
    return vl

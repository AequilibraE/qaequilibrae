import geopandas as gpd
import pandas as pd
from qgis.core import QgsVectorLayer


def geodataframe_from_layer(layer: QgsVectorLayer) -> gpd.GeoDataFrame:
    """Creates a gpd.GeoDataFrame from a data layer."""

    fields = [f.name().lower() for f in layer.fields()]
    rows = []
    geometries = []
    wkbs = []

    for feat in layer.getFeatures():
        rows.append(feat.attributes())

        geom = feat.geometry()
        wkb = bytes(geom.asWkb())

        geometries.append(wkb)
        wkbs.append(wkb)

    df = pd.DataFrame(rows, columns=fields)

    gdf = gpd.GeoDataFrame(df.copy(deep=True), geometry=gpd.GeoSeries.from_wkb(geometries), crs=layer.crs().authid())
    gdf["geoms"] = wkbs
    return gdf

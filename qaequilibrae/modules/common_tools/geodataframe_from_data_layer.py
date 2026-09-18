import geopandas as gpd
import pandas as pd
from qgis.core import QgsFeatureSource


def geodataframe_from_layer(layer: QgsFeatureSource) -> gpd.GeoDataFrame:
    """Creates a GeoDataFrame from a QGIS feature source."""

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

    gdf = gpd.GeoDataFrame(
        df.copy(deep=True),
        geometry=gpd.GeoSeries.from_wkb(geometries),
        crs=layer.sourceCrs().authid(),
    )
    gdf["geoms"] = wkbs
    return gdf

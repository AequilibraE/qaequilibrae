import geopandas as gpd
from qgis.PyQt.QtCore import QMetaType
from qgis.core import QgsField, QgsFeature, QgsGeometry, QgsProject, QgsVectorLayer


def layer_from_geodataframe(gdf: gpd.GeoDataFrame, layer_name: str):
    """Transform GeoDataFrame to QGIS LineString vector layer in memory"""

    # create layer
    crs = gdf.crs.__dict__["srs"]
    vl = QgsVectorLayer(f"LineString?crs={crs}", layer_name, "memory")
    pr = vl.dataProvider()

    # add fields
    def qgs_type(ftype):
        return (
            QMetaType.Type.Double
            if "float" in ftype.name
            else QMetaType.Type.LongLong if "int" in ftype.name else QMetaType.Type.QString
        )

    field_names = list(gdf.dtypes.index)
    field_names.remove("geometry")
    types = [qgs_type(gdf.dtypes[fname]) for fname in field_names]
    attributes = [QgsField(fname, dtype) for fname, dtype in zip(field_names, types)]
    pr.addAttributes(attributes)
    vl.updateFields()

    # Add records
    features = []
    for _, record in gdf.iterrows():
        fet = QgsFeature()

        if record.geometry is not None:
            geom = QgsGeometry.fromWkt(record.geometry.wkt)
            fet.setGeometry(geom)

        fet.setAttributes(record.tolist()[:-1])
        features.append(fet)
    pr.addFeatures(features)

    QgsProject.instance().addMapLayer(vl)

    # returns the layer handle
    return vl

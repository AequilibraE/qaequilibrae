import pandas as pd
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsProject


def layer_from_dataframe(df: pd.DataFrame, layer_name: str) -> QgsVectorLayer:
    # create layer
    vl = QgsVectorLayer("none", layer_name, "memory")
    pr = vl.dataProvider()

    # add fields
    def qgs_type(ftype):
        return QVariant.Double if "float" in ftype.name else QVariant.Int if "int" in ftype.name else QVariant.String

    field_names = list(df.dtypes.index)
    types = [qgs_type(df.dtypes[fname]) for fname in field_names]
    attributes = [QgsField(fname, dtype) for fname, dtype in zip(field_names, types)]
    pr.addAttributes(attributes)
    vl.updateFields()  # tell the vector layer to fetch changes from the provider

    # Add records
    features = []
    for _, record in df.iterrows():
        fet = QgsFeature()
        fet.setAttributes(record.to_list())
        features.append(fet)
    pr.addFeatures(features)
    QgsProject.instance().addMapLayer(vl)

    # returns the layer handle
    return vl

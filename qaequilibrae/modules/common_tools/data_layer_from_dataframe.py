import pandas as pd
from qgis.core import QgsProject, QgsVectorLayer

from .vector_layer_helpers import add_dataframe_features, fields_from_dataframe


def layer_from_dataframe(df: pd.DataFrame, layer_name: str) -> QgsVectorLayer:
    # create layer
    vl = QgsVectorLayer("none", layer_name, "memory")
    pr = vl.dataProvider()

    fields = fields_from_dataframe(df)
    pr.addAttributes(list(fields))
    vl.updateFields()  # tell the vector layer to fetch changes from the provider

    add_dataframe_features(df, pr, fields)

    QgsProject.instance().addMapLayer(vl)

    # returns the layer handle
    return vl

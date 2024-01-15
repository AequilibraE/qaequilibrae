import pandas as pd
from qgis.core import QgsProject

from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe


def test_layer_from_dataframe(qgis_iface):
    path_to_csv = "test/data/SiouxFalls_project/SiouxFalls_od.csv"

    df = pd.read_csv(path_to_csv)
    df["str_col"] = "string column"

    layer = layer_from_dataframe(df[:15], "data_layer")

    assert layer.isValid()

    counter = 0
    for f in layer.getFeatures():
        counter += 1
    print(counter)

    for f in layer.fields():
       print(f)
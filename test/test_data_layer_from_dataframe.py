import pandas as pd

from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe


def test_layer_from_dataframe():
    """A dataframe becomes a layer whose features carry the same values, row for row."""
    data = {"id": [1, 2, 3], "name": ["foo", "bar", "car"]}
    df = pd.DataFrame(data)

    vl = layer_from_dataframe(df, "from_dataframe")

    for idx, f in enumerate(vl.getFeatures()):
        assert f.attributes() == [data["id"][idx], data["name"][idx]]

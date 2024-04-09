from qgis.core import QgsProject
from qaequilibrae.modules.matrix_procedures.load_result_table import load_result_table


def test_load_result_table():
    path = "/workspaces/drive_d/.OuterLoop/.QAequilibrae/.read results/example_sioux_falls_3"

    _ = load_result_table(path, "aon")

    layer = QgsProject.instance().mapLayersByName("aon")[0]
    for feat in layer.getFeatures():
        print(feat.attributes())
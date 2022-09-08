from os.path import join

from qgis._core import QgsProject, QgsVectorLayer, QgsDataSourceUri

import qgis


def load_result_table(project_base_path: str, table_name: str) -> QgsVectorLayer:
    pth = join(project_base_path, "results_database.sqlite")
    conn = qgis.utils.spatialite_connect(pth)
    conn.execute("PRAGMA temp_store = 0;")
    conn.execute("SELECT InitSpatialMetaData();")
    conn.commit()
    conn.close()

    uri = QgsDataSourceUri()
    uri.setDatabase(pth)
    uri.setDataSource("", table_name, None)
    lyr = QgsVectorLayer(uri.uri(), table_name, "spatialite")
    QgsProject.instance().addMapLayer(lyr)
    return lyr

import pandas as pd
import sqlite3
from os.path import join

from qgis.utils import spatialite_connect
from qgis._core import QgsProject, QgsVectorLayer, QgsDataSourceUri


def load_result_table(project_base_path: str, table_name: str) -> QgsVectorLayer:
    pth = join(project_base_path, "results_database.sqlite")
    conn = sqlite3.connect(pth)

    return pd.read_sql(f"select * from {table_name};", con=conn)
    # conn = spatialite_connect(pth)
    # conn.execute("PRAGMA temp_store = 0;")
    # conn.execute("SELECT InitSpatialMetaData();")
    # conn.commit()
    # conn.close()

    # uri = QgsDataSourceUri()
    # uri.setDatabase(pth)
    # uri.setDataSource("", table_name, None)
    # lyr = QgsVectorLayer(uri.uri(), table_name, "spatialite")
    # QgsProject.instance().addMapLayer(lyr)
    # return lyr
    
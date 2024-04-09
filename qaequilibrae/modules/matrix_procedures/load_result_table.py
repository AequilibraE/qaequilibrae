from os.path import join
from os import listdir
from aequilibrae.utils.db_utils import commit_and_close
from aequilibrae.utils.spatialite_utils import connect_spatialite

from qgis._core import QgsProject, QgsVectorLayer, QgsDataSourceUri


def load_result_table(project_base_path: str, table_name: str) -> QgsVectorLayer:
    pth = join(project_base_path, "results_database.sqlite")
    with commit_and_close(connect_spatialite(pth)) as conn:
        conn.execute("PRAGMA temp_store = 0;")
        conn.execute("SELECT InitSpatialMetaData();")

    uri = QgsDataSourceUri()
    uri.setDatabase(pth)
    uri.setDataSource("", table_name, None)
    lyr = QgsVectorLayer(uri.uri(), table_name, "spatialite")
    QgsProject.instance().addMapLayer(lyr)
    return lyr

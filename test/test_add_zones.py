import pytest
from time import sleep
from aequilibrae.utils.db_utils import commit_and_close
from aequilibrae.project.database_connection import database_connection
from qgis.core import QgsGeometry, QgsFeature, QgsVectorLayer
from qgis.core import QgsPointXY, QgsField, QgsProject
from PyQt5.QtCore import QVariant

from qaequilibrae.modules.project_procedures.adds_zones_dialog import AddZonesDialog


def __add_polygon(x1, x2, y1, y2):
    return QgsGeometry.fromPolygonXY(
        [[QgsPointXY(x1, y1), QgsPointXY(x1, y2), QgsPointXY(x2, y2), QgsPointXY(x2, y1), QgsPointXY(x1, y1)]]
    )


def create_zoning_layer():
    squares = []

    x1 = -71.3671  # minx
    x2 = -71.1425  # maxx
    y1 = -30.1181  # miny
    y2 = -29.8006  # maxy
    x_avg = (x1 + x2) / 2
    y_avg = (y1 + y2) / 2

    coords = [[x1, x_avg, y1, y_avg], [x_avg, x2, y1, y_avg], [x1, x_avg, y_avg, y2], [x_avg, x2, y_avg, y2]]

    for c in coords:
        square_geom = __add_polygon(*c)
        squares.append(square_geom)

    vl = QgsVectorLayer("Polygon?crs=EPSG:4326", "squares", "memory")
    pr = vl.dataProvider()

    pr.addAttributes([QgsField("zone_id", QVariant.Int)])
    vl.updateFields()
    for idx, sq in enumerate(squares):
        feature = QgsFeature()
        feature.setGeometry(sq)
        feature.setAttributes([idx + 1])
        pr.addFeature(feature)

    vl.updateExtents()
    QgsProject.instance().addMapLayer(vl)
    return vl


def test_add_zones(pt_project):
    layer = create_zoning_layer()

    dialog = AddZonesDialog(pt_project)
    dialog.chb_add_centroids.setChecked(True)

    dialog.changed_layer()
    dialog.run()

    sleep(2)

    with commit_and_close(database_connection("network")) as conn:
        num_zones = conn.execute("select count(zone_id) from zones").fetchone()[0]

    assert num_zones == 4

    QgsProject.instance().removeMapLayer(layer)

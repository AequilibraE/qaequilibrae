from qgis.core import QgsGeometry, QgsFeature, QgsVectorLayer
from qgis.core import QgsPointXY, QgsField, QgsProject
from PyQt5.QtCore import QVariant

from qaequilibrae.modules.gis.least_common_denominator_dialog import LeastCommonDenominatorDialog


def __add_polygon(x1, x2, y1, y2):
    return QgsGeometry.fromPolygonXY(
        [[QgsPointXY(x1, y1), QgsPointXY(x1, y2), QgsPointXY(x2, y2), QgsPointXY(x2, y1), QgsPointXY(x1, y1)]]
    )


def create_zoning_layer(field_name, x1, x2, y1, y2):
    rectangles = []

    # x1 = -71.3671  # minx
    # x2 = -71.1425  # maxx
    # y1 = -30.1181  # miny
    # y2 = -29.8006  # maxy
    x_avg = (x1 + x2) / 2
    y_avg = (y1 + y2) / 2

    coords = [[x1, x_avg, y1, y_avg], [x_avg, x2, y1, y_avg], [x1, x_avg, y_avg, y2], [x_avg, x2, y_avg, y2]]

    for c in coords:
        rect_geom = __add_polygon(*c)
        rectangles.append(rect_geom)

    vl = QgsVectorLayer("Polygon?crs=EPSG:4326", field_name, "memory")
    pr = vl.dataProvider()

    pr.addAttributes([QgsField("zone_id", QVariant.Int)])
    vl.updateFields()
    for idx, sq in enumerate(rectangles):
        feature = QgsFeature()
        feature.setGeometry(sq)
        feature.setAttributes([idx + 1])
        pr.addFeature(feature)

    vl.updateExtents()
    QgsProject.instance().addMapLayer(vl)
    return vl


def test_least_common_denominator(pt_project):
    dialog = LeastCommonDenominatorDialog(pt_project)
    dialog._testing = True

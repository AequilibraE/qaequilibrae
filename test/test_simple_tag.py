import pytest
from aequilibrae.utils.db_utils import commit_and_close
from aequilibrae.project.database_connection import database_connection
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qgis.core import QgsFeature, QgsPointXY, QgsGeometry
from qgis.PyQt.QtCore import QVariant

from qaequilibrae.modules.gis.simple_tag_dialog import SimpleTagDialog
from qaequilibrae.modules.gis.simple_tag_procedure import SimpleTAG


linestring_assertions = {
    "polygon": {
        "ENCLOSED": ["La Flor del Aire", None, "Pasaje Las Rosas"],
        "TOUCHING": ["Escorial", None, "Lautaro"],
        "CLOSEST": ["Tres Árboles", "centroid connector zone 98", "Circunvalación Monjitas Oriente"],
    },
    "linestring": {
        "TOUCHING": [None, None, None],
        "CLOSEST": ["Óscar Quiroz Morgado", "centroid connector zone 98", "Guatemala"],
    },
    "point": {"CLOSEST": ["centroid connector zone 97", "centroid connector zone 98", "centroid connector zone 99"]},
}


def create_nodes_layer(index):
    layer = QgsVectorLayer("Point?crs=epsg:4326", "point", "memory")
    if not layer.isValid():
        print("Nodes layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        field_zone_id = QgsField("zone_id", QVariant.Int)
        nickname = QgsField("name", QVariant.String)

        layer.dataProvider().addAttributes([field_id, field_zone_id, nickname])
        layer.updateFields()

        points = [
            QgsPointXY(-71.2489, -29.8936),
            QgsPointXY(-71.2355, -29.8947),
            QgsPointXY(-71.2350, -29.8875),
        ]

        attributes = (index, [None, None, None])

        features = []
        for i, (point, zone_id, name) in enumerate(zip(points, *attributes)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(point))
            feature.setAttributes([i + 1, zone_id, name])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(layer)

    return layer


def create_links_layer(index):
    layer = QgsVectorLayer("Linestring?crs=epsg:4326", "linestring", "memory")
    if not layer.isValid():
        print("linestring layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        field_zone_id = QgsField("zone_id", QVariant.Int)
        nickname = QgsField("name", QVariant.String)

        layer.dataProvider().addAttributes([field_id, field_zone_id, nickname])
        layer.updateFields()

        lines = [
            [QgsPointXY(-71.2517, -29.8880), QgsPointXY(-71.2498, -29.8944)],
            [QgsPointXY(-71.2389, -29.8943), QgsPointXY(-71.2342, -29.8933)],
            [QgsPointXY(-71.2397, -29.8836), QgsPointXY(-71.2341, -29.8805)],
        ]

        attributes = (index, [None, None, None])

        features = []
        for i, (line, zone_id, name) in enumerate(zip(lines, *attributes)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolylineXY(line))
            feature.setAttributes([i + 1, zone_id, name])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(layer)

    return layer


def create_polygons_layer(index):
    layer = QgsVectorLayer("Polygon?crs=epsg:4326", "polygon", "memory")
    if not layer.isValid():
        print("Polygon layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        field_zone_id = QgsField("zone_id", QVariant.Int)
        nickname = QgsField("name", QVariant.String)

        layer.dataProvider().addAttributes([field_id, field_zone_id, nickname])
        layer.updateFields()

        polys = [
            [
                QgsPointXY(-71.2487, -29.8936),
                QgsPointXY(-71.2487, -29.8895),
                QgsPointXY(-71.2441, -29.8895),
                QgsPointXY(-71.2441, -29.8936),
                QgsPointXY(-71.2487, -29.8936),
            ],
            [
                QgsPointXY(-71.2401, -29.8945),
                QgsPointXY(-71.2401, -29.8928),
                QgsPointXY(-71.2375, -29.8928),
                QgsPointXY(-71.2375, -29.8945),
                QgsPointXY(-71.2401, -29.8945),
            ],
            [
                QgsPointXY(-71.2329, -29.8800),
                QgsPointXY(-71.2329, -29.8758),
                QgsPointXY(-71.2280, -29.8758),
                QgsPointXY(-71.2280, -29.8800),
                QgsPointXY(-71.2329, -29.8800),
            ],
        ]

        attributes = (index, [None, None, None])

        features = []
        for i, (poly, zone_id, name) in enumerate(zip(polys, *attributes)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolygonXY([poly]))
            feature.setAttributes([i + 1, zone_id, name])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(layer)

    return layer


@pytest.mark.parametrize("ops", ["ENCLOSED", "TOUCHING", "CLOSEST"])
@pytest.mark.parametrize("to_layer", ["polygon", "linestring", "point"])
def test_simple_tag_polygon(coquimbo_project, to_layer, ops):
    if to_layer == "point" and ops == "TOUCHING":
        pytest.skip(f"'{ops}' does not apply to polygon-{to_layer}")

    coquimbo_project.load_layer_by_name("zones")

    zones = [97, 98, 99]
    authors = ["Valparaiso", "Santiago", "Antofagasta"]

    with commit_and_close(database_connection("network")) as conn:
        for i, zone in enumerate(zones):
            conn.execute(f"UPDATE zones SET name='{authors[i]}' WHERE zone_id={zone}")
        conn.execute("DELETE FROM zones WHERE name IS NULL;")

    if to_layer == "polygon":
        layer = create_polygons_layer(zones)
    elif to_layer == "linestring":
        layer = create_links_layer(zones)
    else:
        layer = create_nodes_layer(zones)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert to_layer in prj_layers
    assert "zones" in prj_layers

    dialog = SimpleTagDialog(coquimbo_project)

    dialog.fromlayer.setCurrentText("zones")
    dialog.fromfield.setCurrentIndex(3)
    dialog.tolayer.setCurrentText(to_layer)
    dialog.tofield.setCurrentIndex(2)

    dialog.set_from_fields()
    dialog.set_to_fields()
    dialog.set_available_operations()

    dialog.worker_thread = SimpleTAG(
        parentThread=coquimbo_project.iface.mainWindow(),
        flayer="zones",
        ffield="name",
        tlayer=to_layer,
        tfield="name",
        fmatch=None,
        tmatch=None,
        operation=ops,
        geo_types=dialog.geography_types,
    )
    dialog.worker_thread.doWork()

    feats = [f["name"] for f in layer.getFeatures()]
    assert "Santiago" in feats
    if ops in ["TOUCHING", "CLOSEST"] or to_layer == "point":
        assert "Valparaiso" in feats
    elif ops in ["CLOSEST"] or to_layer == "point":
        assert "Antofagasta" in feats

    QgsProject.instance().clear()


@pytest.mark.parametrize("ops", ["ENCLOSED", "TOUCHING", "CLOSEST"])
@pytest.mark.parametrize("to_layer", ["polygon", "linestring", "point"])
def test_simple_tag_linestring(coquimbo_project, to_layer, ops):
    if to_layer != "polygon" and ops == "ENCLOSED":
        pytest.skip(f"'{ops}' does not apply to linestring-{to_layer}")
    if to_layer == "point" and ops == "TOUCHING":
        pytest.skip(f"'{ops}' does not apply to linestring-{to_layer}")

    coquimbo_project.load_layer_by_name("links")

    nodes = [21, 121, 1021]

    if to_layer == "polygon":
        layer = create_polygons_layer(nodes)
    elif to_layer == "linestring":
        layer = create_links_layer(nodes)
    else:
        layer = create_nodes_layer(nodes)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert to_layer in prj_layers
    assert "links" in prj_layers

    dialog = SimpleTagDialog(coquimbo_project)

    dialog.fromlayer.setCurrentText("links")
    dialog.fromfield.setCurrentIndex(3)
    dialog.tolayer.setCurrentText(to_layer)
    dialog.tofield.setCurrentIndex(2)

    dialog.set_from_fields()
    dialog.set_to_fields()
    dialog.set_available_operations()

    dialog.worker_thread = SimpleTAG(
        parentThread=coquimbo_project.iface.mainWindow(),
        flayer="links",
        ffield="name",
        tlayer=to_layer,
        tfield="name",
        fmatch=None,
        tmatch=None,
        operation=ops,
        geo_types=dialog.geography_types,
    )
    dialog.worker_thread.doWork()

    feats = [f["name"] for f in layer.getFeatures()]
    print(feats)
    # assert "Santiago" in feats
    # if ops in ["TOUCHING", "CLOSEST"] or to_layer == "point":
    #     assert "Valparaiso" in feats
    # elif ops in ["CLOSEST"] or to_layer == "point":
    #     assert "Antofagasta" in feats
    if to_layer == "polygon":
        assert feats == linestring_assertions["polygon"][ops]

    QgsProject.instance().clear()


@pytest.mark.parametrize("ops", ["ENCLOSED", "CLOSEST"])
@pytest.mark.parametrize("to_layer", ["polygon", "linestring", "point"])
def test_simple_tag_point(coquimbo_project, to_layer, ops):
    if to_layer != "polygon" and ops == "ENCLOSED":
        pytest.skip(f"'{ops}' does not apply to point-{to_layer}")

    coquimbo_project.load_layer_by_name("nodes")

    nodes = [21, 121, 1021]

    if to_layer == "polygon":
        layer = create_polygons_layer(nodes)
    elif to_layer == "linestring":
        layer = create_links_layer(nodes)
    else:
        layer = create_nodes_layer(nodes)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert to_layer in prj_layers
    assert "nodes" in prj_layers

    # dialog = SimpleTagDialog(coquimbo_project)

    # dialog.fromlayer.setCurrentText("nodes")
    # dialog.fromfield.setCurrentIndex(3)
    # dialog.tolayer.setCurrentText(to_layer)
    # dialog.tofield.setCurrentIndex(2)

    # dialog.set_from_fields()
    # dialog.set_to_fields()
    # dialog.set_available_operations()

    # dialog.worker_thread = SimpleTAG(
    #     parentThread=coquimbo_project.iface.mainWindow(),
    #     flayer="nodes",
    #     ffield="name",
    #     tlayer=to_layer,
    #     tfield="name",
    #     fmatch=None,
    #     tmatch=None,
    #     operation=ops,
    #     geo_types=dialog.geography_types,
    # )
    # dialog.worker_thread.doWork()

    # feats = [f["name"] for f in layer.getFeatures()]
    # print(feats)
    # assert "Santiago" in feats
    # if ops in ["TOUCHING", "CLOSEST"] or to_layer == "point":
    #     assert "Valparaiso" in feats
    # elif ops in ["CLOSEST"] or to_layer == "point":
    #     assert "Antofagasta" in feats

    QgsProject.instance().clear()

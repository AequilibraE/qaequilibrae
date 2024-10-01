import sqlite3
from pathlib import Path
from os.path import join
import pytest
from aequilibrae.utils.db_utils import commit_and_close
from aequilibrae.project.database_connection import database_connection
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qgis.core import QgsFeature, QgsPointXY, QgsGeometry
from qgis.PyQt.QtCore import QVariant

from qaequilibrae.modules.gis.simple_tag_dialog import SimpleTagDialog
from qaequilibrae.modules.gis.simple_tag_procedure import SimpleTAG


def create_nodes_layer(index):
    layer = QgsVectorLayer("Point?crs=epsg:4326", "Centroids", "memory")
    if not layer.isValid():
        print("Nodes layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        field_zone_id = QgsField("zone_id", QVariant.Int)
        nickname = QgsField("name", QVariant.String)

        layer.dataProvider().addAttributes([field_id])
        layer.dataProvider().addAttributes([field_zone_id])
        layer.dataProvider().addAttributes([nickname])
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


@pytest.mark.parametrize("ops", ["ENCLOSED", "CLOSEST"])
def test_simple_tag_polygon_and_point(coquimbo_project, ops):
    # Load zoning layer
    coquimbo_project.load_layer_by_name("zones")

    zones = [97, 98, 99]
    cities = ["Valparaiso", "Santiago", "Antofagasta"]

    with commit_and_close(database_connection("network")) as conn:
        for i, zone in enumerate(zones):
            conn.execute(f"UPDATE zones SET name='{cities[i]}' WHERE zone_id={zone}")

    nodes_layer = create_nodes_layer(zones)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "Centroids" in prj_layers
    assert "zones" in prj_layers

    dialog = SimpleTagDialog(coquimbo_project)

    dialog.fromlayer.setCurrentText("zones")
    dialog.fromfield.setCurrentIndex(3)
    dialog.tolayer.setCurrentText("Centroids")
    dialog.tofield.setCurrentIndex(2)

    dialog.set_from_fields()
    dialog.set_to_fields()
    dialog.set_available_operations()

    dialog.worker_thread = SimpleTAG(
        parentThread=coquimbo_project.iface.mainWindow(),
        flayer="zones",
        ffield="name",
        tlayer="Centroids",
        tfield="name",
        fmatch=None,
        tmatch=None,
        operation=ops,
        geo_types=dialog.geography_types,
    )
    dialog.worker_thread.doWork()

    feats = [f["name"] for f in nodes_layer.getFeatures()]
    assert feats == cities

    QgsProject.instance().clear()


@pytest.mark.skip("Not ready")
def test_simple_tag_polygon_and_linestring(coquimbo_project):

    coquimbo_project.load_layer_by_name("zones")

    authors = ["Pablo Neruda", "Gabriela Mistral", "Alejandro Zambra"]

    with commit_and_close(database_connection("network")) as conn:
        for i, zone in enumerate([97, 98, 99]):
            conn.execute(f"UPDATE zones SET name='{authors[i]}' WHERE zone_id={zone}")

    # links_layer =

    zones = join(coquimbo_project.project.project_base_path, "project_database.sqlite")
    con = sqlite3.connect(zones)

    print(con.execute("SELECT zone_id, name, population FROM zones WHERE zone_id IN (97, 98, 99)").fetchall())


def test_simple_tag_linestring_and_point(coquimbo_project):
    coquimbo_project.load_layer_by_name("links")

    links = [21, 121, 1021]

    nodes_layer = create_nodes_layer(links)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "Centroids" in prj_layers
    assert "links" in prj_layers

    dialog = SimpleTagDialog(coquimbo_project)

    dialog.fromlayer.setCurrentText("links")
    dialog.fromfield.setCurrentIndex(8)
    dialog.tolayer.setCurrentText("Centroids")
    dialog.tofield.setCurrentIndex(2)

    dialog.set_from_fields()
    dialog.set_to_fields()
    dialog.set_available_operations()

    dialog.worker_thread = SimpleTAG(
        parentThread=coquimbo_project.iface.mainWindow(),
        flayer="links",
        ffield="name",
        tlayer="Centroids",
        tfield="name",
        fmatch=None,
        tmatch=None,
        operation="CLOSEST",
        geo_types=dialog.geography_types,
    )
    dialog.worker_thread.doWork()

    feats = [f["name"] for f in nodes_layer.getFeatures()]
    assert feats == ["centroid connector zone 97", "centroid connector zone 98", "centroid connector zone 99"]

    QgsProject.instance().clear()

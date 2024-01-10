import pytest
from time import sleep
from shapely.geometry import Point
from aequilibrae.utils.db_utils import commit_and_close
from aequilibrae.project.database_connection import database_connection
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qgis.core import QgsFeature, QgsPointXY, QgsGeometry
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt import QtWidgets

from qaequilibrae.modules.network.adds_connectors_dialog import AddConnectorsDialog


def test_add_connectors_from_zones(pt_no_feed):
    dialog = AddConnectorsDialog(pt_no_feed)
    dialog.rdo_zone.setChecked(True)
    dialog._testing = True

    zoning = dialog.project.zoning
    assert len(zoning.all_zones())

    dialog.run()

    sleep(2)

    dialog.project.network.links.refresh()
    dialog.project.network.nodes.refresh()

    with commit_and_close(database_connection("network")) as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

        conn.execute("delete from links where name like 'centroid%'")
        conn.execute("delete from nodes where is_centroid=1")

    assert node_count == 11
    assert link_count == 11


@pytest.mark.parametrize(
    ("node_id", "radius", "point"),
    [
        (100, 500, Point(-29.9170, -71.3183)),
        (101, 5555, Point(-71.3346, -29.9176)),
    ],
)
def test_add_connectors_from_network(pt_no_feed, node_id, radius, point):
    dialog = AddConnectorsDialog(pt_no_feed)
    dialog.rdo_network.setChecked(True)

    # Add a node to the network
    nodes = dialog.project.network.nodes
    nd = nodes.new_centroid(node_id)
    nd.geometry = point
    nd.save()

    dialog.lst_modes.setCurrentRow(1)
    dialog.lst_link_types.setCurrentRow(11)

    dialog.sb_radius.setValue(radius)

    dialog.run()

    assert dialog.sb_radius.value() == radius

    sleep(2)

    dialog.project.network.links.refresh()
    dialog.project.network.nodes.refresh()

    with commit_and_close(database_connection("network")) as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

        conn.execute("delete from links where name like 'centroid%'")
        conn.execute("delete from nodes where is_centroid=1")

    if radius == 500:
        assert node_count == 1
        assert link_count == 0
    else:
        assert node_count == 1
        assert link_count == 1


def test_add_connectors_from_layer(pt_no_feed):
    nodes_layer = QgsVectorLayer("Point?crs=epsg:4326", "Centroids", "memory")
    if not nodes_layer.isValid():
        print("Nodes layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        nodes_layer.dataProvider().addAttributes([field_id])

        field_zone_id = QgsField("zone_id", QVariant.Int)
        nodes_layer.dataProvider().addAttributes([field_zone_id])

        nodes_layer.updateFields()
        points = [
            QgsPointXY(-71.3509, -29.9393),
            QgsPointXY(-71.3182, -29.9619),
            QgsPointXY(12.4606, 41.9093),
        ]

        zone_ids = [97, 98, 99]

        features = []
        for i, (point, zone_id) in enumerate(zip(points, zone_ids)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(point))
            feature.setAttributes([i + 1, zone_id])
            features.append(feature)

        nodes_layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(nodes_layer)

    dialog = AddConnectorsDialog(pt_no_feed)
    dialog.rdo_layer.setChecked(True)

    dialog.lst_modes.setCurrentRow(1)
    dialog.lst_link_types.setCurrentRow(11)

    dialog.run()

    sleep(2)

    dialog.project.network.links.refresh()
    dialog.project.network.nodes.refresh()

    with commit_and_close(database_connection("network")) as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

        conn.execute("delete from links where name like 'centroid%'")
        conn.execute("delete from nodes where is_centroid=1")

    assert node_count == 3
    assert link_count == 2

    QgsProject.instance().removeMapLayer(nodes_layer.id())

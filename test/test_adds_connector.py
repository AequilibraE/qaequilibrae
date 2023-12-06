import os
import sqlite3
import pytest
from shapely.geometry import Point
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qgis.core import QgsFeature, QgsPointXY, QgsGeometry
from qgis.PyQt.QtCore import QVariant

from qaequilibrae.modules.network.adds_connectors_dialog import AddConnectorsDialog


def test_add_connectors_from_zones(pt_project):
    dialog = AddConnectorsDialog(pt_project)
    dialog.rdo_zone.setChecked(True)

    # Checks if there is a zone system in the project
    zoning = dialog.project.zoning
    assert len(zoning.all_zones())

    dialog.lst_modes.setCurrentRow(1)
    dialog.lst_link_types.setCurrentRow(11)

    dialog.run()

    db_path = os.path.join(pt_project.project.project_base_path, "project_database.sqlite")
    conn = sqlite3.connect(db_path)
    node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
    link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

    assert node_count == 11
    assert link_count == 11

    conn.execute("delete from links where name like 'centroid%'")
    conn.execute("delete from nodes where is_centroid=1")
    conn.commit()


@pytest.mark.parametrize(
    ("node_id", "radius", "point"), [(1000, 500, Point(-96.90, 43.4907)), (1001, 5555, Point(-96.90, 43.4910))]
)
def test_add_connectors_from_network(ae_with_project, node_id, radius, point):
    dialog = AddConnectorsDialog(ae_with_project)
    dialog.rdo_network.setChecked(True)

    # Add a node to the network
    nodes = dialog.project.network.nodes
    nd = nodes.new_centroid(node_id)
    nd.geometry = point
    nd.save()

    dialog.lst_link_types.setCurrentRow(1)
    dialog.lst_modes.setCurrentRow(3)

    dialog.sb_radius.setValue(radius)

    dialog.run()

    assert dialog.sb_radius.value() == radius

    db_path = os.path.join(ae_with_project.project.project_base_path, "project_database.sqlite")
    conn = sqlite3.connect(db_path)
    node_count = conn.execute("select count(node_id) from nodes where modes is null").fetchone()[0]
    link_count = conn.execute("select count(name) from links where name is not null").fetchone()[0]

    if radius == 500:
        assert node_count == 1
        assert link_count == 0
    else:
        assert node_count == 2
        assert link_count == 2

@pytest.mark.skip("Test is crashing")
def test_add_connectors_from_layer(ae_with_project):
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
            QgsPointXY(-96.7433, 43.5839),
            QgsPointXY(-96.7689, 43.5176),
            QgsPointXY(12.4606599, 41.9093632),
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

    dialog = AddConnectorsDialog(ae_with_project)
    dialog.rdo_layer.setChecked(True)

    dialog.lst_link_types.setCurrentRow(1)
    dialog.lst_modes.setCurrentRow(3)

    dialog.run()

    db_path = os.path.join(ae_with_project.project.project_base_path, "project_database.sqlite")
    conn = sqlite3.connect(db_path)
    var = conn.execute("select count(node_id) from nodes where modes is null").fetchone()[0]
    assert var == 5

    # Due to the radius, not all nodes are connected to the network
    var = conn.execute("select count(name) from links where name is not null").fetchone()[0]
    assert var == 2  # check the validity of this assertion!

    QgsProject.instance().removeMapLayer(nodes_layer.id())

    conn.execute("delete from links where name like 'centroid%'")
    conn.commit()

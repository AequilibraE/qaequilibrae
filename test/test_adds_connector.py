import os
import sqlite3
import pytest
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qgis.core import QgsFeature, QgsPointXY, QgsGeometry
from qgis.PyQt.QtCore import QVariant

from qaequilibrae.modules.network.adds_connectors_dialog import AddConnectorsDialog


def load_layer():

    nodes_layer = QgsVectorLayer("Point?crs=epsg:4326", "Nodes layer", "memory")
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


@pytest.mark.skip("not working yet")  
def test_add_connectors_from_zones(ae_with_project, qtbot):
    dialog = AddConnectorsDialog(ae_with_project)
    dialog.rdo_zone.setChecked(True)

    # Checks if there is a zone system in the project
    zoning = dialog.project.zoning
    assert len(zoning.all_zones())

    # dialog.lst_link_types.setCurrentRow(0)
    # dialog.lst_modes.setCurrentRow(3)

    # dialog.run()

    # Assert in the links and nodes tables that the connector was created.

@pytest.mark.skip("not working yet")
def test_add_connectors_from_network(ae_with_project):
    dialog = AddConnectorsDialog(ae_with_project)
    dialog.rdo_network.setChecked(True)

    # dialog.lst_link_types.setCurrentRow(0)
    # dialog.lst_modes.setCurrentRow(3)

    # dialog.run()

    # Assert in the links and nodes tables that the connector was created.


def test_add_connectors_from_layer(ae_with_project):
    load_layer() # load points layer

    dialog = AddConnectorsDialog(ae_with_project)
    dialog.rdo_layer.setChecked(True)

    dialog.lst_link_types.setCurrentRow(1)
    dialog.lst_modes.setCurrentRow(3)

    dialog.run()

    db_path = os.path.join(ae_with_project.project.project_base_path, "project_database.sqlite")
    conn = sqlite3.connect(db_path)
    var = conn.execute("select count(name) from links where name is not null").fetchone()[0]
    assert var == 2

    var = conn.execute("select count(node_id) from nodes where modes is null").fetchone()[0]
    assert var == 3
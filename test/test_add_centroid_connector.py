import pytest
from qgis.core import QgsProject
from shapely.geometry import Point

from qaequilibrae.modules.network.adds_connectors_dialog import AddConnectorsDialog
from qaequilibrae.modules.network.adds_connectors_procedure import AddsConnectorsProcedure
from .utilities import create_centroids_layer


@pytest.mark.parametrize("in_zone", [True, False])
def test_add_connectors_from_zones_dialog(pt_no_feed, in_zone):
    dialog = AddConnectorsDialog(pt_no_feed)
    dialog.rdo_zone.setChecked(True)
    dialog.chb_zone.setChecked(in_zone)

    dialog.lst_modes.setCurrentRow(1)
    dialog.lst_link_types.setCurrentRow(11)

    # Assert zones exist in the project
    zoning = dialog.project.zoning
    assert len(zoning.all_zones())

    dialog.run()

    with dialog.project.db_connection as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

    assert node_count == 11 and link_count == 11


def test_add_connectors_from_zones_procedure(pt_no_feed):
    dialog = AddConnectorsDialog(pt_no_feed)
    dialog.source = "zone"

    zoning = dialog.project.zoning
    assert len(zoning.all_zones())

    parameters = {
        "qgis_project": dialog.qgis_project,
        "link_types": ["p"],
        "modes": ["c"],
        "num_connectors": 2,
        "source": "zone",
        "limit_to_zone": False,
    }

    dialog.worker_thread = AddsConnectorsProcedure(pt_no_feed.iface.mainWindow(), **parameters)
    dialog.worker_thread.doWork()

    with dialog.project.db_connection as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

    assert node_count == 11 and link_count == 22


@pytest.mark.parametrize(
    ("node_id", "radius", "point"),
    [
        (100, 500, Point(-29.9170, -71.3183)),
        (101, 5555, Point(-71.3346, -29.9176)),
    ],
)
def test_add_connectors_from_network_dialog(pt_no_feed, node_id, radius, point):
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

    with dialog.project.db_connection as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

    if radius == 500:
        assert node_count == 1 and link_count == 0
    else:
        assert node_count == 1 and link_count == 1


def test_add_connectors_from_network_procedure(
    pt_no_feed,
):
    dialog = AddConnectorsDialog(pt_no_feed)

    nodes = dialog.project.network.nodes
    nd = nodes.new_centroid(101)
    nd.geometry = Point(-71.3346, -29.9176)
    nd.save()

    parameters = {
        "qgis_project": dialog.qgis_project,
        "link_types": ["p"],
        "modes": ["c"],
        "num_connectors": 1,
        "source": "network",
        "radius": 5555,
    }

    dialog.worker_thread = AddsConnectorsProcedure(pt_no_feed.iface.mainWindow(), **parameters)
    dialog.worker_thread.doWork()

    with dialog.project.db_connection as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

    assert node_count == 1 and link_count == 1


def test_add_connectors_from_layer_dialog(pt_no_feed):
    create_centroids_layer()

    dialog = AddConnectorsDialog(pt_no_feed)
    dialog.rdo_layer.setChecked(True)

    dialog.set_fields()

    dialog.lst_modes.setCurrentRow(1)
    dialog.lst_link_types.setCurrentRow(11)

    dialog.run()

    with dialog.project.db_connection as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

    assert node_count == 3 and link_count == 2


def test_add_connectors_from_layer_procedure(pt_no_feed):
    create_centroids_layer()

    nodes_layer = QgsProject.instance().mapLayersByName("Centroids")[0]

    dialog = AddConnectorsDialog(pt_no_feed)

    parameters = {
        "qgis_project": dialog.qgis_project,
        "link_types": ["p"],
        "modes": ["c"],
        "num_connectors": 1,
        "source": "layer",
        "radius": 3000,
        "layer": nodes_layer,
        "field": "ID",
    }

    dialog.worker_thread = AddsConnectorsProcedure(pt_no_feed.iface.mainWindow(), **parameters)
    dialog.worker_thread.doWork()

    with dialog.project.db_connection as conn:
        node_count = conn.execute("select count(node_id) from nodes where is_centroid=1").fetchone()[0]
        link_count = conn.execute("select count(name) from links where name like 'centroid connector%'").fetchone()[0]

    assert node_count == 3 and link_count == 2

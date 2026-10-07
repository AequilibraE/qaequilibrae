"""Exercise network construction through Processing without plugin dialogs."""

import pytest
from qgis.PyQt.QtCore import QMetaType
from qgis.core import QgsProcessingContext, QgsProcessingException, QgsProcessingFeedback
from shapely.geometry import LineString, Point, Polygon

from qaequilibrae.modules.processing_provider.model_building.centroids import (
    AddCentroidConnectors,
    AddCentroidsFromZones,
)
from qaequilibrae.modules.processing_provider.model_building.create_project import (
    CreateProjectFromLinkLayer,
    CreateProjectFromOSM,
)
from qaequilibrae.modules.processing_provider.model_building.renumber_nodes import RenumberNodesFromLayer
from qaequilibrae.modules.processing_provider.project import borrow_project

from . import test_processing_geometry_io as geometry_io_tests
from .test_processing_geometry_io import _run_algorithm

source_layer_factory = geometry_io_tests.source_layer_factory


def link_layer(factory):
    return factory(
        "links",
        "LineString",
        [
            ("road_id", QMetaType.Type.Int),
            ("dir", QMetaType.Type.Int),
            ("allowed", QMetaType.Type.QString),
            ("kind", QMetaType.Type.QString),
            ("custom_cost", QMetaType.Type.Double),
        ],
        [
            (LineString([(0, 0), (0.01, 0)]), [42, 0, "c", "road", 12.5]),
            (LineString([(0.01, 0), (0.02, 0)]), [43, 0, "c", "road", 8.5]),
        ],
    )


def create_from_links(factory, folder, **extra):
    parameters = {
        "INPUT": link_layer(factory),
        "DIRECTION": "dir",
        "MODES": "allowed",
        "LINK_TYPE": "kind",
        "SOURCE_ID": "road_id",
        "OUTPUT": str(folder),
        **extra,
    }
    result, _ = _run_algorithm(CreateProjectFromLinkLayer(), parameters)
    return result


def test_create_from_links_preserves_attributes_and_source_ids(source_layer_factory, tmp_path):
    folder = tmp_path / "network"
    assert create_from_links(source_layer_factory, folder)["OUTPUT"] == str(folder)
    with borrow_project(folder) as project:
        data = project.network.links.data
        assert data.source_id.tolist() == [42, 43]
        assert data.custom_cost.tolist() == [12.5, 8.5]
        assert project.network.count_nodes() == 3
        assert project.network.nodes.data.node_id.min() >= 10000


def test_create_from_links_can_skip_extra_fields(source_layer_factory, tmp_path):
    folder = tmp_path / "network"
    create_from_links(source_layer_factory, folder, COPY_FIELDS=False)
    with borrow_project(folder) as project:
        assert "custom_cost" not in project.network.links.data
        assert project.network.links.data.source_id.tolist() == [42, 43]


def test_create_from_links_rejects_existing_folder(source_layer_factory, tmp_path):
    algorithm = CreateProjectFromLinkLayer()
    algorithm.initAlgorithm()
    with pytest.raises(QgsProcessingException, match="must not exist"):
        algorithm.processAlgorithm(
            {
                "INPUT": link_layer(source_layer_factory),
                "DIRECTION": "dir",
                "MODES": "allowed",
                "LINK_TYPE": "kind",
                "OUTPUT": str(tmp_path),
            },
            QgsProcessingContext(),
            QgsProcessingFeedback(),
        )


def centroid_layer(factory, rows):
    return factory("centroids", "Point", [("zone", QMetaType.Type.Int)], rows)


def test_centroid_import_renumbers_nodes_and_link_endpoints(source_layer_factory, tmp_path):
    folder = tmp_path / "network"
    create_from_links(source_layer_factory, folder)
    layer = centroid_layer(source_layer_factory, [(Point(0, 0), [1]), (Point(0.03, 0), [2])])
    result, _ = _run_algorithm(
        RenumberNodesFromLayer(), {"PROJECT_FOLDER": str(folder), "INPUT": layer, "NODE_ID": "zone"}
    )
    assert result == {"ADDED": 1, "RENUMBERED": 1, "MATCHED": 1}
    with borrow_project(folder) as project:
        assert project.network.nodes.get(1).is_centroid == 1
        assert project.network.nodes.get(2).is_centroid == 1
        assert 1 in set(project.network.links.data.a_node) | set(project.network.links.data.b_node)
    result, _ = _run_algorithm(
        RenumberNodesFromLayer(), {"PROJECT_FOLDER": str(folder), "INPUT": layer, "NODE_ID": "zone"}
    )
    assert result == {"ADDED": 0, "RENUMBERED": 0, "MATCHED": 2}


def test_centroid_import_allows_id_swaps(source_layer_factory, tmp_path):
    folder = tmp_path / "network"
    create_from_links(source_layer_factory, folder)
    with borrow_project(folder) as project:
        rows = list(project.network.nodes.data.itertuples())
    layer = centroid_layer(
        source_layer_factory, [(rows[0].geometry, [rows[1].node_id]), (rows[1].geometry, [rows[0].node_id])]
    )
    result, _ = _run_algorithm(
        RenumberNodesFromLayer(), {"PROJECT_FOLDER": str(folder), "INPUT": layer, "NODE_ID": "zone"}
    )
    assert result["RENUMBERED"] == 2
    with borrow_project(folder) as project:
        assert project.network.nodes.get(rows[0].node_id).geometry.equals(rows[1].geometry)
        assert project.network.nodes.get(rows[1].node_id).geometry.equals(rows[0].geometry)


@pytest.mark.parametrize(
    "rows, error",
    [
        ([(Point(0, 0), [1]), (Point(0.01, 0), [1])], "unique"),
        ([(Point(0, 0), [1]), (Point(0, 0), [2])], "unique"),
        ([(Point(0.03, 0), [10000])], "already in use"),
    ],
)
def test_centroid_import_rejects_conflicts_before_changes(source_layer_factory, tmp_path, rows, error):
    folder = tmp_path / "network"
    create_from_links(source_layer_factory, folder)
    algorithm = RenumberNodesFromLayer()
    algorithm.initAlgorithm()
    with pytest.raises(QgsProcessingException, match=error):
        algorithm.processAlgorithm(
            {"PROJECT_FOLDER": str(folder), "INPUT": centroid_layer(source_layer_factory, rows), "NODE_ID": "zone"},
            QgsProcessingContext(),
            QgsProcessingFeedback(),
        )
    with borrow_project(folder) as project:
        assert project.network.count_centroids() == 0
        assert project.network.count_nodes() == 3


def add_zone(folder):
    with borrow_project(folder) as project:
        zone = project.zoning.new(1)
        zone.geometry = Polygon([(-0.001, -0.002), (0.003, -0.002), (0.003, 0.002), (-0.001, 0.002)])
        zone.save()


def test_centroids_from_zones_are_idempotent(source_layer_factory, tmp_path):
    folder = tmp_path / "network"
    create_from_links(source_layer_factory, folder)
    add_zone(folder)
    assert _run_algorithm(AddCentroidsFromZones(), {"PROJECT_FOLDER": str(folder)})[0] == {"ADDED": 1}
    assert _run_algorithm(AddCentroidsFromZones(), {"PROJECT_FOLDER": str(folder)})[0] == {"ADDED": 0}


def test_connectors_create_centroids_and_connect_network(source_layer_factory, tmp_path):
    folder = tmp_path / "network"
    create_from_links(source_layer_factory, folder)
    add_zone(folder)
    result, _ = _run_algorithm(
        AddCentroidConnectors(), {"PROJECT_FOLDER": str(folder), "FROM_ZONES": True, "MODES": "c"}
    )
    assert result["ADDED"] == 1
    with borrow_project(folder) as project:
        assert project.network.count_centroids() == 1
        assert project.network.count_links() == 3
        assert 1 in set(project.network.links.data.a_node) | set(project.network.links.data.b_node)


def test_connectors_validate_modes_before_adding_centroids(source_layer_factory, tmp_path):
    folder = tmp_path / "network"
    create_from_links(source_layer_factory, folder)
    add_zone(folder)
    algorithm = AddCentroidConnectors()
    algorithm.initAlgorithm()
    with pytest.raises(QgsProcessingException, match="Unknown mode"):
        algorithm.processAlgorithm(
            {"PROJECT_FOLDER": str(folder), "FROM_ZONES": True, "MODES": "!"},
            QgsProcessingContext(),
            QgsProcessingFeedback(),
        )
    with borrow_project(folder) as project:
        assert project.network.count_centroids() == 0


@pytest.mark.parametrize("selection", [{"PLACE": "Example"}, {"EXTENT": "0,1,0,1 [EPSG:4326]"}])
def test_osm_import_calls_model_api_without_a_dialog(monkeypatch, tmp_path, selection):
    from aequilibrae.project.network.network import Network

    calls = []
    monkeypatch.setattr(Network, "create_from_osm", lambda self, **kwargs: calls.append(kwargs))
    result, _ = _run_algorithm(CreateProjectFromOSM(), {"OUTPUT": str(tmp_path / "osm"), **selection})
    assert result["OUTPUT"] == str(tmp_path / "osm")
    assert len(calls) == 1
    if "PLACE" in selection:
        assert calls[0]["place_name"] == "Example"
    else:
        assert calls[0]["model_area"].bounds == (0, 0, 1, 1)
    assert calls[0]["modes"] == ["car", "transit", "bicycle", "walk"]


@pytest.mark.parametrize("selection", [{}, {"PLACE": "Example", "EXTENT": "0,1,0,1"}])
def test_osm_requires_exactly_one_area(tmp_path, selection):
    algorithm = CreateProjectFromOSM()
    algorithm.initAlgorithm()
    with pytest.raises(QgsProcessingException, match="either"):
        algorithm.processAlgorithm(
            {"OUTPUT": str(tmp_path / "osm"), **selection}, QgsProcessingContext(), QgsProcessingFeedback()
        )
    assert not (tmp_path / "osm").exists()


def test_create_from_links_adds_new_modes_and_keeps_standard_directional_fields(source_layer_factory, tmp_path):
    layer = source_layer_factory(
        "links",
        "LineString",
        [
            ("direction", QMetaType.Type.Int),
            ("modes", QMetaType.Type.QString),
            ("link_type", QMetaType.Type.QString),
            ("speed_ab", QMetaType.Type.Double),
        ],
        [(LineString([(0, 0), (0.01, 0)]), [0, "z", "new_road", 30.0])],
    )
    folder = tmp_path / "network"
    _run_algorithm(
        CreateProjectFromLinkLayer(),
        {"INPUT": layer, "DIRECTION": "direction", "MODES": "modes", "LINK_TYPE": "link_type", "OUTPUT": str(folder)},
    )
    with borrow_project(folder) as project:
        assert "z" in project.network.modes.all_modes()
        assert project.network.links.data.speed_ab.tolist() == [30.0]


def test_project_creation_restores_active_project(ae_with_project, source_layer_factory, tmp_path):
    from aequilibrae.context import get_active_project

    active = get_active_project()
    create_from_links(source_layer_factory, tmp_path / "network")
    assert get_active_project() is active

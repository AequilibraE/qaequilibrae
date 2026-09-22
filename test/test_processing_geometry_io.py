import pytest
from aequilibrae import Project
from qgis.PyQt.QtCore import QMetaType
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorLayer,
)
from shapely.geometry import Point

from qaequilibrae.modules.processing_provider.data_procedures.add_link_type import AddLinkType
from qaequilibrae.modules.processing_provider.data_procedures.add_mode import AddMode
from qaequilibrae.modules.processing_provider.geometry_io.add import AddLinks, AddNodes, AddZones
from qaequilibrae.modules.processing_provider.geometry_io.extract import ExtractLinks, ExtractNodes, ExtractZones
from qaequilibrae.modules.processing_provider.geometry_io.modify import ModifyLinks, ModifyNodes, ModifyZones
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm


def _project_data(project_path, table_name):
    project = Project()
    project.open(project_path)
    try:
        data = project.zoning.data if table_name == "zones" else getattr(project.network, table_name).data
        return data.copy()
    finally:
        project.close()


def _record_attributes(project_path, table_name, identifier, fields):
    project = Project()
    project.open(project_path)
    try:
        table = project.zoning if table_name == "zones" else getattr(project.network, table_name)
        record = table.get(identifier)
        return {field: getattr(record, field) for field in fields}
    finally:
        project.close()


def _run_algorithm(algorithm, parameters):
    algorithm.initAlgorithm()
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    feedback = QgsProcessingFeedback()
    results, succeeded = algorithm.run(parameters, context, feedback)
    assert succeeded, feedback.textLog()
    return results, context


@pytest.fixture
def source_layer_factory():
    created_layers = []

    def create_layer(name, geometry_type, fields, rows):
        layer = QgsVectorLayer(f"{geometry_type}?crs=EPSG:4326", name, "memory")
        assert layer.isValid()
        layer.dataProvider().addAttributes([QgsField(field_name, field_type) for field_name, field_type in fields])
        layer.updateFields()

        features = []
        for geometry, attributes in rows:
            feature = QgsFeature(layer.fields())
            feature.setGeometry(QgsGeometry.fromWkt(geometry.wkt))
            feature.setAttributes(attributes)
            features.append(feature)
        assert layer.dataProvider().addFeatures(features)[0]
        QgsProject.instance().addMapLayer(layer)
        created_layers.append(layer)
        return layer

    yield create_layer

    for layer in created_layers:
        QgsProject.instance().removeMapLayer(layer.id())


@pytest.mark.parametrize(
    ("algorithm_type", "table_name", "identifier_field"),
    [
        (ExtractLinks, "links", "link_id"),
        (ExtractNodes, "nodes", "node_id"),
        (ExtractZones, "zones", "zone_id"),
    ],
)
def test_extract_algorithms_output_project_features(sioux_falls_project_path, algorithm_type, table_name, identifier_field):
    expected = _project_data(sioux_falls_project_path, table_name)

    results, context = _run_algorithm(
        algorithm_type(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "OUTPUT": "TEMPORARY_OUTPUT",
        },
    )

    output = context.takeResultLayer(results["OUTPUT"])
    assert output is not None
    assert output.featureCount() == len(expected)
    assert identifier_field in [field.name() for field in output.fields()]
    assert all(not feature.geometry().isEmpty() for feature in output.getFeatures())


def test_add_links(sioux_falls_project_path, source_layer_factory):
    row = _project_data(sioux_falls_project_path, "links").iloc[0]
    before = len(_project_data(sioux_falls_project_path, "links"))
    layer = source_layer_factory(
        "new_links",
        "LineString",
        [
            ("direction", QMetaType.Type.LongLong),
            ("modes", QMetaType.Type.QString),
            ("link_type", QMetaType.Type.QString),
        ],
        [(row.geometry, [int(row.direction), str(row.modes), str(row.link_type)])],
    )

    _run_algorithm(
        AddLinks(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "INPUT": layer,
        },
    )

    assert len(_project_data(sioux_falls_project_path, "links")) == before + 1


def test_add_nodes_defaults_to_a_non_centroid(sioux_falls_project_path, source_layer_factory):
    row = _project_data(sioux_falls_project_path, "nodes").iloc[0]
    geometry = Point(row.geometry.x + 0.001, row.geometry.y + 0.001)
    layer = source_layer_factory(
        "new_regular_node",
        "Point",
        [("node_id", QMetaType.Type.LongLong)],
        [(geometry, [9998])],
    )

    _run_algorithm(
        AddNodes(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "INPUT": layer,
        },
    )

    assert _record_attributes(sioux_falls_project_path, "nodes", 9998, ["is_centroid"])["is_centroid"] == 0


def test_add_nodes(sioux_falls_project_path, source_layer_factory):
    row = _project_data(sioux_falls_project_path, "nodes").iloc[0]
    before = len(_project_data(sioux_falls_project_path, "nodes"))
    geometry = Point(row.geometry.x + 0.001, row.geometry.y + 0.001)
    layer = source_layer_factory(
        "new_nodes",
        "Point",
        [("node_id", QMetaType.Type.LongLong), ("is_centroid", QMetaType.Type.LongLong)],
        [(geometry, [9999, 1])],
    )

    _run_algorithm(
        AddNodes(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "INPUT": layer,
        },
    )

    assert len(_project_data(sioux_falls_project_path, "nodes")) == before + 1
    assert _record_attributes(sioux_falls_project_path, "nodes", 9999, ["is_centroid"])["is_centroid"] == 1


def test_add_zones(sioux_falls_project_path, source_layer_factory):
    row = _project_data(sioux_falls_project_path, "zones").iloc[0]
    before = len(_project_data(sioux_falls_project_path, "zones"))
    layer = source_layer_factory(
        "new_zones",
        "Polygon",
        [("zone_id", QMetaType.Type.LongLong), ("name", QMetaType.Type.QString)],
        [(row.geometry, [9999, "new zone"])],
    )

    _run_algorithm(
        AddZones(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "INPUT": layer,
        },
    )

    assert len(_project_data(sioux_falls_project_path, "zones")) == before + 1
    assert _record_attributes(sioux_falls_project_path, "zones", 9999, ["name"])["name"] == "new zone"


def test_modify_links(sioux_falls_project_path, source_layer_factory):
    row = _project_data(sioux_falls_project_path, "links").iloc[0]
    direction = 0 if int(row.direction) != 0 else 1
    layer = source_layer_factory(
        "modified_links",
        "LineString",
        [("link_id", QMetaType.Type.LongLong), ("direction", QMetaType.Type.LongLong), ("modes", QMetaType.Type.QString), ("link_type", QMetaType.Type.QString)],
        [(row.geometry, [int(row.link_id), direction, str(row.modes), str(row.link_type)])],
    )

    _run_algorithm(
        ModifyLinks(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "INPUT": layer,
        },
    )

    assert _record_attributes(sioux_falls_project_path, "links", int(row.link_id), ["direction"])["direction"] == direction


def test_modify_nodes(sioux_falls_project_path, source_layer_factory):
    row = _project_data(sioux_falls_project_path, "nodes").iloc[0]
    layer = source_layer_factory(
        "modified_nodes",
        "Point",
        [("node_id", QMetaType.Type.LongLong), ("is_centroid", QMetaType.Type.LongLong)],
        [(row.geometry, [int(row.node_id), 0])],
    )

    _run_algorithm(
        ModifyNodes(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "INPUT": layer,
        },
    )

    assert _record_attributes(sioux_falls_project_path, "nodes", int(row.node_id), ["is_centroid"])["is_centroid"] == 0


def test_modify_zones(sioux_falls_project_path, source_layer_factory):
    row = _project_data(sioux_falls_project_path, "zones").iloc[0]
    layer = source_layer_factory(
        "modified_zones",
        "Polygon",
        [("zone_id", QMetaType.Type.LongLong), ("name", QMetaType.Type.QString)],
        [(row.geometry, [int(row.zone_id), "updated zone"])],
    )

    _run_algorithm(
        ModifyZones(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "INPUT": layer,
        },
    )

    assert _record_attributes(sioux_falls_project_path, "zones", int(row.zone_id), ["name"])["name"] == "updated zone"


def test_add_link_type(sioux_falls_project_path):
    results, _ = _run_algorithm(
        AddLinkType(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "LINK_TYPE_ID": "q",
            "LINK_TYPE": "arterial",
            "DESCRIPTION": "arterial streets",
            "LANES": 3,
            "LANE_CAPACITY": 1200,
            "SPEED": 50,
        },
    )

    assert results["LINK_TYPE_ID"] == "q"
    project = Project()
    project.open(sioux_falls_project_path)
    try:
        link_type = project.network.link_types.all_types()["q"]
        assert (link_type.link_type, link_type.description, link_type.lanes, link_type.lane_capacity) == (
            "arterial",
            "arterial streets",
            3,
            1200,
        )
        # Sioux Falls does not have a speed column in its link type schema.
        assert getattr(link_type, "speed", None) is None
    finally:
        project.close()


def test_add_mode(sioux_falls_project_path):
    results, _ = _run_algorithm(
        AddMode(),
        {
            ProjectAlgorithm.PROJECT_FOLDER: sioux_falls_project_path,
            "MODE_ID": "q",
            "MODE_NAME": "scooter",
            "DESCRIPTION": "scooters",
            "PCE": 1.2,
            "VOT": 20,
            "PPV": 1.5,
        },
    )

    assert results["MODE_ID"] == "q"
    project = Project()
    project.open(sioux_falls_project_path)
    try:
        mode = project.network.modes.all_modes()["q"]
        assert (mode.mode_name, mode.description, mode.pce, mode.vot, mode.ppv) == ("scooter", "scooters", 1.2, 20, 1.5)
    finally:
        project.close()

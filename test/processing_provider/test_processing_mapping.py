from os.path import join
from shutil import copytree

import numpy as np
import pytest
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

from qaequilibrae.modules.processing_provider.mapping_procedures.delaunay_network import DelaunayNetwork
from qaequilibrae.modules.processing_provider.mapping_procedures.desire_lines import DesireLines, compute_desire_lines
from qaequilibrae.modules.processing_provider.mapping_procedures.simple_tag import SimpleTag, match_features


def _run_algorithm(algorithm, parameters):
    algorithm.initAlgorithm()
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    feedback = QgsProcessingFeedback()
    results, succeeded = algorithm.run(parameters, context, feedback)
    assert succeeded, feedback.textLog()
    return results, context


def _make_layer(name, geometry_type, rows, fields):
    layer = QgsVectorLayer(f"{geometry_type}?crs=EPSG:4326", name, "memory")
    assert layer.isValid()
    layer.dataProvider().addAttributes([QgsField(field_name, field_type) for field_name, field_type in fields])
    layer.updateFields()

    features = []
    for wkt, attributes in rows:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        feature.setAttributes(attributes)
        features.append(feature)
    assert layer.dataProvider().addFeatures(features)[0]
    return layer


def _values(layer, field_name):
    return [feature[field_name] for feature in layer.getFeatures()]


def test_match_features_closest_uses_real_distance():
    source = _make_layer(
        "source_points",
        "Point",
        [("POINT (0 0)", ["a"]), ("POINT (10 0)", ["b"])],
        [("tag", QMetaType.Type.QString)],
    )
    target = _make_layer(
        "target_points",
        "Point",
        [("POINT (1 0)", [None]), ("POINT (9 0)", [None])],
        [("name", QMetaType.Type.QString)],
    )

    results, context = _run_algorithm(
        SimpleTag(),
        {
            SimpleTag.SOURCE: source,
            SimpleTag.SOURCE_FIELD: "tag",
            SimpleTag.TARGET: target,
            SimpleTag.TARGET_FIELD: "name",
            SimpleTag.OPERATION: 0,
            SimpleTag.OUTPUT: "TEMPORARY_OUTPUT",
        },
    )

    output = context.takeResultLayer(results[SimpleTag.OUTPUT])
    assert output is not None
    assert _values(output, "name") == ["a", "b"]


def test_match_features_enclosed_adds_new_field():
    source = _make_layer(
        "source_polygons",
        "Polygon",
        [
            ("POLYGON ((0 0, 0 2, 2 2, 2 0, 0 0))", ["inner"]),
            ("POLYGON ((5 5, 5 7, 7 7, 7 5, 5 5))", ["outer"]),
        ],
        [("tag", QMetaType.Type.QString)],
    )
    target = _make_layer(
        "target_points",
        "Point",
        [("POINT (1 1)", [1]), ("POINT (6 6)", [2])],
        [("id", QMetaType.Type.Int)],
    )

    results, context = _run_algorithm(
        SimpleTag(),
        {
            SimpleTag.SOURCE: source,
            SimpleTag.SOURCE_FIELD: "tag",
            SimpleTag.TARGET: target,
            SimpleTag.TARGET_FIELD: "name",
            SimpleTag.OPERATION: 1,
            SimpleTag.OUTPUT: "TEMPORARY_OUTPUT",
        },
    )

    output = context.takeResultLayer(results[SimpleTag.OUTPUT])
    assert output is not None
    assert [field.name() for field in output.fields()] == ["id", "name"]
    assert _values(output, "name") == ["inner", "outer"]


def test_match_features_touching_keeps_largest_shared_edge():
    source = _make_layer(
        "source_polygons",
        "Polygon",
        [
            ("POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))", ["small"]),
            ("POLYGON ((1 0, 1 4, 4 4, 4 0, 1 0))", ["large"]),
        ],
        [("tag", QMetaType.Type.QString)],
    )
    target = _make_layer(
        "target_line",
        "LineString",
        [("LINESTRING (0 0.5, 3 0.5)", [None])],
        [("name", QMetaType.Type.QString)],
    )

    results, context = _run_algorithm(
        SimpleTag(),
        {
            SimpleTag.SOURCE: source,
            SimpleTag.SOURCE_FIELD: "tag",
            SimpleTag.TARGET: target,
            SimpleTag.TARGET_FIELD: "name",
            SimpleTag.OPERATION: 2,
            SimpleTag.OUTPUT: "TEMPORARY_OUTPUT",
        },
    )

    output = context.takeResultLayer(results[SimpleTag.OUTPUT])
    assert output is not None
    assert _values(output, "name") == ["large"]


def test_matching_fields_must_be_selected_as_a_pair():
    source = _make_layer(
        "source",
        "Point",
        [("POINT (0 0)", ["a", "x"])],
        [("tag", QMetaType.Type.QString), ("match", QMetaType.Type.QString)],
    )
    target = _make_layer("target", "Point", [("POINT (0 0)", [None])], [("name", QMetaType.Type.QString)])

    algorithm = SimpleTag()
    algorithm.initAlgorithm()
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    results, succeeded = algorithm.run(
        {
            SimpleTag.SOURCE: source,
            SimpleTag.SOURCE_FIELD: "tag",
            SimpleTag.TARGET: target,
            SimpleTag.TARGET_FIELD: "name",
            SimpleTag.OPERATION: 0,
            SimpleTag.MATCH_SOURCE_FIELD: "match",
            SimpleTag.OUTPUT: "TEMPORARY_OUTPUT",
        },
        context,
        QgsProcessingFeedback(),
    )

    assert not succeeded
    assert results == {}


def test_matching_fields_restrict_the_source():
    source = _make_layer(
        "source_polygons",
        "Polygon",
        [
            ("POLYGON ((0 0, 0 5, 5 5, 5 0, 0 0))", ["zone-a", "a"]),
            ("POLYGON ((0 0, 0 5, 5 5, 5 0, 0 0))", ["zone-b", "b"]),
        ],
        [("tag", QMetaType.Type.QString), ("match", QMetaType.Type.QString)],
    )
    target = _make_layer(
        "target_points",
        "Point",
        [("POINT (1 1)", [None, "b"])],
        [("name", QMetaType.Type.QString), ("match", QMetaType.Type.QString)],
    )

    parameters = {
        SimpleTag.SOURCE: source,
        SimpleTag.SOURCE_FIELD: "tag",
        SimpleTag.TARGET: target,
        SimpleTag.TARGET_FIELD: "name",
        SimpleTag.OPERATION: 1,
        SimpleTag.MATCH_SOURCE_FIELD: "match",
        SimpleTag.MATCH_TARGET_FIELD: "match",
        SimpleTag.OUTPUT: "TEMPORARY_OUTPUT",
    }
    results, context = _run_algorithm(SimpleTag(), parameters)

    output = context.takeResultLayer(results[SimpleTag.OUTPUT])
    assert output is not None
    assert _values(output, "name") == ["zone-b"]


def test_match_features_skips_features_without_a_match():
    source = _make_layer(
        "source_polygon",
        "Polygon",
        [("POLYGON ((0 0, 0 2, 2 2, 2 0, 0 0))", ["a"])],
        [("tag", QMetaType.Type.QString)],
    )
    target = _make_layer(
        "target_points",
        "Point",
        [("POINT (1 1)", [None]), ("POINT (100 100)", [None])],
        [("name", QMetaType.Type.QString)],
    )
    target_features = list(target.getFeatures())

    matches = match_features(
        list(source.getFeatures()),
        target_features,
        source_value_index=0,
        operation="ENCLOSED",
        source_is_polygon=True,
    )

    assert matches == {target_features[0].id(): "a"}


@pytest.fixture
def fresh_sioux_falls_project_path(folder_path, example_project_templates):
    copytree(example_project_templates["sioux_falls"], folder_path)
    return folder_path


def test_desire_lines_from_matrix(sioux_falls_project_path):
    points = _make_layer(
        "zones",
        "Point",
        [(f"POINT ({zone} {zone % 5})", [zone]) for zone in range(1, 25)],
        [("zone_id", QMetaType.Type.Int)],
    )

    results, context = _run_algorithm(
        DesireLines(),
        {
            DesireLines.ZONES: points,
            DesireLines.ZONE_ID_FIELD: "zone_id",
            DesireLines.MATRIX_PATH: join(sioux_falls_project_path, "matrices", "demand.omx"),
            DesireLines.MATRIX_CORES: "matrix",
            DesireLines.OUTPUT: "TEMPORARY_OUTPUT",
        },
    )

    output = context.takeResultLayer(results[DesireLines.OUTPUT])
    assert output is not None
    assert output.featureCount() > 0
    field_names = [field.name() for field in output.fields()]
    assert "matrix_AB" in field_names
    assert "matrix_BA" in field_names


def test_empty_desire_lines_keep_output_schema():
    class EmptyMatrix:
        view_names = ["car"]
        index = np.array([1, 2])

        @staticmethod
        def get_matrix(core):
            return np.zeros((2, 2))

    dataframe, report, unassigned = compute_desire_lines({1: (0.0, 0.0), 2: (1.0, 1.0)}, EmptyMatrix())

    assert dataframe.empty
    assert list(dataframe.columns) == [
        "link_id",
        "a_node",
        "b_node",
        "direction",
        "distance",
        "car_AB",
        "car_BA",
        "geometry",
    ]
    assert not report
    assert unassigned == 0


def test_desire_lines_unassigned_flow_excludes_intrazonals():
    class Matrix:
        view_names = ["car"]
        index = np.array([1, 2])

        @staticmethod
        def get_matrix(core):
            return np.array([[100.0, 3.0], [4.0, 200.0]])

    _, report, unassigned = compute_desire_lines({1: (0.0, 0.0)}, Matrix())

    assert unassigned == 7.0
    assert report == ["Zone 2 does not have a corresponding centroid/zone. Total flow 7.0"]


def test_desire_lines_orient_flow_by_zone_id_not_matrix_position():
    class Matrix:
        view_names = ["car"]
        index = np.array([20, 10])

        @staticmethod
        def get_matrix(core):
            return np.array([[0.0, 2.0], [3.0, 0.0]])

    dataframe, _, _ = compute_desire_lines({10: (0.0, 0.0), 20: (1.0, 1.0)}, Matrix())

    assert len(dataframe) == 1
    row = dataframe.iloc[0]
    assert (row.a_node, row.b_node) == (20, 10)
    assert (row.car_AB, row.car_BA) == (2.0, 3.0)


def test_delaunay_network_builds_without_matrix():
    nodes = _make_layer(
        "nodes",
        "Point",
        [("POINT (0 0)", [1]), ("POINT (2 0)", [2]), ("POINT (1 2)", [3]), ("POINT (3 2)", [4])],
        [("node_id", QMetaType.Type.Int)],
    )
    results, context = _run_algorithm(
        DelaunayNetwork(),
        {
            DelaunayNetwork.NODES: nodes,
            DelaunayNetwork.NODE_ID_FIELD: "node_id",
            DelaunayNetwork.OUTPUT: "TEMPORARY_OUTPUT",
        },
    )

    output = context.takeResultLayer(results[DelaunayNetwork.OUTPUT])
    assert output is not None
    assert output.featureCount() > 0
    field_names = [field.name() for field in output.fields()]
    assert {"link_id", "direction", "a_node", "b_node", "distance"}.issubset(field_names)
    assert not any(field.endswith(("_ab", "_ba", "_tot")) for field in field_names)


def test_delaunay_network_builds_and_assigns_matrix(fresh_sioux_falls_project_path):
    nodes = _make_layer(
        "nodes",
        "Point",
        [(f"POINT ({zone} {zone % 5})", [zone]) for zone in range(1, 25)],
        [("node_id", QMetaType.Type.Int)],
    )
    results, context = _run_algorithm(
        DelaunayNetwork(),
        {
            DelaunayNetwork.NODES: nodes,
            DelaunayNetwork.NODE_ID_FIELD: "node_id",
            DelaunayNetwork.MATRIX_PATH: join(fresh_sioux_falls_project_path, "matrices", "demand.omx"),
            DelaunayNetwork.MATRIX_CORES: "matrix",
            DelaunayNetwork.OUTPUT: "TEMPORARY_OUTPUT",
        },
    )

    output = context.takeResultLayer(results[DelaunayNetwork.OUTPUT])
    assert output is not None
    assert output.featureCount() > 0
    assert any(field.name().endswith("_tot") for field in output.fields())

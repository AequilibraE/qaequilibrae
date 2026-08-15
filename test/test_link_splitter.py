from qgis.core import QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayerUtils

from qaequilibrae.modules.common_tools.link_splitter import LinkSplitter, line_vertices, split_at


def _points(*coordinates):
    return [QgsPointXY(x, y) for x, y in coordinates]


def _coordinates(pieces):
    return [[(vertex.x(), vertex.y()) for vertex in piece] for piece in pieces]


def _node_coordinates(project, node_ids):
    """Where the given nodes sit, in the order they were asked for."""
    with project.db_connection as conn:
        found = dict(
            conn.execute(
                "SELECT node_id, AsText(geometry) FROM nodes WHERE node_id IN ({})".format(
                    ",".join("?" * len(node_ids))
                ),
                node_ids,
            ).fetchall()
        )

    return [tuple(float(part) for part in found[node_id][6:-1].split()) for node_id in node_ids]


def _links_layer(ae):
    """The links layer, on the map where a layer being digitized into would be."""
    ae.load_layer_by_name("links")
    return ae.layers["links"][0]


def _digitize(layer, vertices):
    """Adds a feature the way the digitizing tool does, defaults and all."""
    fields = layer.fields()
    attributes = {
        fields.indexOf("modes"): "c",
        fields.indexOf("link_type"): "default",
        fields.indexOf("direction"): 0,
    }
    feature = QgsVectorLayerUtils.createFeature(layer, QgsGeometry.fromPolylineXY(vertices), attributes)
    layer.addFeature(feature)


def _committed_links(project, link_ids):
    with project.db_connection as conn:
        return conn.execute(
            "SELECT link_id, a_node, b_node FROM links WHERE link_id IN ({}) ORDER BY link_id".format(
                ",".join("?" * len(link_ids))
            ),
            link_ids,
        ).fetchall()


def test_a_line_is_cut_at_every_interior_vertex_sitting_on_a_node():
    """A line crossing two nodes comes back as three stretches."""
    vertices = _points((0, 0), (1, 1), (2, 2), (3, 3))
    pieces = split_at(vertices, {(1.0, 1.0), (2.0, 2.0)})

    assert _coordinates(pieces) == [
        [(0, 0), (1, 1)],
        [(1, 1), (2, 2)],
        [(2, 2), (3, 3)],
    ]


def test_a_line_that_only_meets_nodes_at_its_ends_stays_whole():
    """Nodes at the ends are not interior, so the line is left as one piece."""
    vertices = _points((0, 0), (1, 1), (2, 2))
    pieces = split_at(vertices, {(0.0, 0.0), (2.0, 2.0)})

    assert _coordinates(pieces) == [[(0, 0), (1, 1), (2, 2)]]


def test_a_vertex_repeated_on_a_node_does_not_make_a_link_of_no_length():
    """A duplicated vertex on a node splits once, rather than producing a zero-length link."""
    vertices = _points((0, 0), (1, 1), (1, 1), (2, 2))
    pieces = split_at(vertices, {(1.0, 1.0)})

    assert _coordinates(pieces) == [
        [(0, 0), (1, 1)],
        [(1, 1), (1, 1), (2, 2)],
    ]


def test_a_line_revisiting_the_same_node_is_cut_at_both_passes():
    """A line passing the same node twice is cut on both passes."""
    vertices = _points((0, 0), (1, 1), (2, 0), (1, 1), (0, 2))
    pieces = split_at(vertices, {(1.0, 1.0)})

    assert len(pieces) == 3


def test_multipart_geometry_is_only_read_when_it_holds_a_single_line():
    """Multipart geometries are only read when they hold one line; anything else is left alone."""
    single = QgsGeometry.fromMultiPolylineXY([_points((0, 0), (1, 1))])
    several = QgsGeometry.fromMultiPolylineXY([_points((0, 0), (1, 1)), _points((2, 2), (3, 3))])

    assert len(line_vertices(single)) == 2
    assert line_vertices(several) == []
    assert line_vertices(QgsGeometry()) == []


def test_digitizing_through_a_node_leaves_one_link_per_stretch(ae_with_project, qtbot):
    """A link drawn across a node commits as two links sharing that node, with no node added."""
    project = ae_with_project.project
    layer = _links_layer(ae_with_project)
    first, middle, last = _node_coordinates(project, [1, 2, 6])

    layer.startEditing()
    _digitize(layer, _points(first, middle, last))
    qtbot.wait(50)  # the split waits for QGIS to close its own digitizing command

    added = list(layer.editBuffer().addedFeatures().values())
    assert len(added) == 2

    geometries = sorted(_coordinates([feature.geometry().asPolyline() for feature in added]))
    assert geometries == sorted([[first, middle], [middle, last]])

    # Ids the layer had not handed out yet, so the commit does not collide on either unique column
    assert sorted(feature["link_id"] for feature in added) == [77, 78]
    assert sorted(feature["ogc_fid"] for feature in added) == [77, 78]

    assert layer.commitChanges(), layer.commitErrors()

    # The database triggers recognise both ends of both pieces, so no new node was created
    assert _committed_links(project, [77, 78]) == [(77, 1, 2), (78, 2, 6)]
    with project.db_connection as conn:
        assert conn.execute("SELECT max(node_id) FROM nodes").fetchone()[0] == 24


def test_a_link_digitized_after_a_split_does_not_reuse_an_id(ae_with_project, qtbot):
    """Digitizing a run of links before saving leaves the pieces in the buffer to be counted."""
    project = ae_with_project.project
    layer = _links_layer(ae_with_project)
    first, middle, last = _node_coordinates(project, [1, 2, 6])

    layer.startEditing()
    _digitize(layer, _points(first, middle, last))
    qtbot.wait(50)
    _digitize(layer, _points((-96.5, 43.5), (-96.4, 43.4)))
    qtbot.wait(50)

    added = layer.editBuffer().addedFeatures().values()
    assert sorted(int(feature["link_id"]) for feature in added) == [77, 78, 79]
    assert sorted(int(feature["ogc_fid"]) for feature in added) == [77, 78, 79]

    assert layer.commitChanges(), layer.commitErrors()


def test_digitizing_clear_of_the_nodes_leaves_a_single_link(ae_with_project, qtbot):
    """A link drawn clear of every node is saved exactly as drawn."""
    layer = _links_layer(ae_with_project)
    first, last = _node_coordinates(ae_with_project.project, [1, 6])
    midpoint = ((first[0] + last[0]) / 2, (first[1] + last[1]) / 2 + 0.01)

    layer.startEditing()
    _digitize(layer, _points(first, midpoint, last))
    qtbot.wait(50)

    assert len(layer.editBuffer().addedFeatures()) == 1

    layer.rollBack()


def test_the_toggle_stops_the_link_from_being_broken(ae_with_project, qtbot):
    """With the option off, a link drawn across a node is saved whole."""
    layer = _links_layer(ae_with_project)
    vertices = _points(*_node_coordinates(ae_with_project.project, [1, 2, 6]))

    LinkSplitter.set_enabled(False)
    try:
        layer.startEditing()
        _digitize(layer, vertices)
        qtbot.wait(50)

        assert len(layer.editBuffer().addedFeatures()) == 1
    finally:
        LinkSplitter.set_enabled(True)
        layer.rollBack()


def test_the_toggle_is_on_by_default_and_survives_being_set(ae_with_project):
    """The option starts on and remembers being switched off and back on."""
    assert LinkSplitter.enabled()

    LinkSplitter.set_enabled(False)
    try:
        assert not LinkSplitter.enabled()
    finally:
        LinkSplitter.set_enabled(True)

    assert LinkSplitter.enabled()


def test_only_the_links_layer_is_watched(ae_with_project):
    """Only the links layer is watched, and it is dropped when removed from the map."""
    splitter = ae_with_project.splitter
    nodes_layer_id = ae_with_project.layers["nodes"][1]
    links_layer_id = ae_with_project.layers["links"][1]

    assert links_layer_id in splitter.watched
    assert nodes_layer_id not in splitter.watched

    splitter.layer_removed(links_layer_id)
    assert links_layer_id not in splitter.watched


def test_a_layer_that_left_the_map_is_not_reached_for(ae_with_project, qtbot):
    """The deferred split runs after the user could have removed the layer from the project."""
    layer = _links_layer(ae_with_project)
    layer_id = layer.id()
    QgsProject.instance().removeMapLayer(layer_id)

    ae_with_project.splitter.split_feature(layer_id, -1)

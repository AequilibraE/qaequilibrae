from qaequilibrae.modules.network.node_numbering import FIRST_NETWORK_NODE_ID, reserve_node_ids_for_centroids


def _new_link(project, wkt):
    """Digitizes a link the way the links layer does, letting the triggers mint its nodes."""
    with project.db_connection as conn:
        conn.execute(
            "INSERT INTO links (link_id, a_node, b_node, modes, link_type, geometry) "
            "VALUES ((select coalesce(max(link_id), 0) + 1 from links), 0, 0, 'c', 'default', "
            "GeomFromText(?, 4326))",
            (wkt,),
        )


def _node_ids(project):
    with project.db_connection as conn:
        return [row[0] for row in conn.execute("SELECT node_id FROM nodes ORDER BY node_id").fetchall()]


def test_nodes_created_by_a_new_link_start_at_the_floor(ae_with_project):
    """Nodes minted for a new link start above the reserved centroid range."""
    project = ae_with_project.project
    existing = _node_ids(project)

    assert max(existing) < FIRST_NETWORK_NODE_ID

    _new_link(project, "LINESTRING(-97.0 43.0, -97.1 43.1)")
    created = sorted(set(_node_ids(project)) - set(existing))

    assert created == [FIRST_NETWORK_NODE_ID, FIRST_NETWORK_NODE_ID + 1]


def test_node_ids_keep_climbing_once_past_the_floor(ae_with_project):
    """Subsequent links keep counting up from there rather than restarting."""
    project = ae_with_project.project
    existing = _node_ids(project)

    _new_link(project, "LINESTRING(-97.0 43.0, -97.1 43.1)")
    _new_link(project, "LINESTRING(-97.2 43.2, -97.3 43.3)")
    created = sorted(set(_node_ids(project)) - set(existing))

    assert created == [FIRST_NETWORK_NODE_ID + i for i in range(4)]


def test_reserving_twice_leaves_the_triggers_alone(ae_with_project):
    """Reserving again is a no-op, so the triggers are not rewritten or nested."""
    project = ae_with_project.project

    with project.db_connection as conn:
        before = dict(conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'trigger'").fetchall())

    reserve_node_ids_for_centroids(project)

    with project.db_connection as conn:
        after = dict(conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'trigger'").fetchall())

    assert after == before


def test_the_floor_can_be_moved_without_nesting_the_expression(ae_with_project):
    """The floor can be set to a different value and takes effect cleanly."""
    project = ae_with_project.project
    reserve_node_ids_for_centroids(project, 500_000)

    _new_link(project, "LINESTRING(-97.0 43.0, -97.1 43.1)")

    assert max(_node_ids(project)) == 500_001


def test_existing_node_ids_are_left_alone(ae_with_project):
    """Nodes already in the model keep the ids they had."""
    project = ae_with_project.project

    assert _node_ids(project) == list(range(1, 25))

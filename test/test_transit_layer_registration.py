"""AequilibraE creates an empty public_transport.sqlite for every project it opens, so the
transit layers must be registered based on the route system's contents, not the file's existence."""

TRANSIT_LAYERS = {"transit_links", "transit_routes", "transit_stops", "transit_pattern_mapping"}


def test_transit_layers_registered_when_project_has_routes(pt_project):
    """A project with a route system gets its transit layers registered."""
    assert TRANSIT_LAYERS.issubset(set(pt_project.layers)), (
        f"coquimbo has a route system, so its transit layers must be registered. Got: {sorted(pt_project.layers)}"
    )


def test_transit_layers_skipped_when_project_has_no_routes(pt_no_feed):
    """A project whose transit database is empty gets no transit layers."""
    assert not TRANSIT_LAYERS & set(pt_no_feed.layers), (
        f"A project with no GTFS feed must not get transit layers. Got: {sorted(pt_no_feed.layers)}"
    )


def test_transit_layers_skipped_for_project_that_never_had_transit(ae_with_project):
    """A project with no transit at all gets no transit layers."""
    assert not TRANSIT_LAYERS & set(ae_with_project.layers), (
        f"SiouxFalls has no transit at all, so it must not get transit layers. Got: {sorted(ae_with_project.layers)}"
    )

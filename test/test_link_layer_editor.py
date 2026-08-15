from qgis.core import QgsFieldConstraints

from qaequilibrae.modules.style_loader.editor_styles import _mode_combinations


def _value_map_items(layer, field_name):
    setup = layer.editorWidgetSetup(layer.fields().indexOf(field_name))
    assert setup.type() == "ValueMap"
    return [next(iter(item.items())) for item in setup.config()["map"]]


def test_mode_combinations_with_a_single_mode():
    """A project with one mode offers exactly that one combination."""
    assert _mode_combinations(["c"]) == [("c", "c")]


def test_mode_combinations_carry_the_spelling_the_links_already_use():
    """Combinations are listed once, sorted, and in whatever order the links already spell them."""
    entries = _mode_combinations(["b", "c", "t", "w"], ["ct", "cwbt"])
    values = [value for _, value in entries]

    # `cwbt` is the same set as `bctw`, and both have to be there: one to pick for a new link,
    # the other so the links already holding it are not shown as an unknown value
    assert "cwbt" in values and "bctw" in values
    assert values.count("ct") == 1
    assert values == sorted(values, key=lambda value: (value.casefold(), value))
    assert all(label == value for label, value in entries)


def test_zone_identifiers_default_to_the_next_available_values(ae_with_project):
    """A new zone is pre-filled with the next zone_id and ogc_fid, computed on insert only."""
    layer = ae_with_project.layers["zones"][0]

    for field_name, expected in (("ogc_fid", 4), ("zone_id", 4)):
        field_index = layer.fields().indexOf(field_name)
        default = layer.defaultValueDefinition(field_index)

        assert default.expression() == f'coalesce(maximum("{field_name}"), 0) + 1'
        assert not default.applyOnUpdate()
        assert layer.defaultValue(field_index) == expected


def test_zone_ids_carry_on_from_a_numbering_of_their_own(pt_no_feed):
    """Zone ids are routinely numbered by hand, so the next one follows the largest in use."""
    layer = pt_no_feed.layers["zones"][0]

    assert layer.defaultValue(layer.fields().indexOf("zone_id")) == 61
    assert layer.defaultValue(layer.fields().indexOf("ogc_fid")) == 12


def test_link_identifiers_default_to_the_next_available_values(ae_with_project):
    """A new link is pre-filled with the next link_id and ogc_fid."""
    layer = ae_with_project.layers["links"][0]

    for field_name in ("ogc_fid", "link_id"):
        field_index = layer.fields().indexOf(field_name)
        default = layer.defaultValueDefinition(field_index)

        assert default.expression() == f'coalesce(maximum("{field_name}"), 0) + 1'
        assert not default.applyOnUpdate()
        assert layer.defaultValue(field_index) == 77


def test_link_nodes_default_to_zero(ae_with_project):
    """a_node and b_node start at zero, since the database triggers work them out."""
    layer = ae_with_project.layers["links"][0]

    for field_name in ("a_node", "b_node"):
        field_index = layer.fields().indexOf(field_name)
        default = layer.defaultValueDefinition(field_index)

        assert default.expression() == "0"
        assert not default.applyOnUpdate()
        assert layer.defaultValue(field_index) == 0


def test_link_nodes_are_hidden_from_the_attribute_form(ae_with_project):
    """a_node and b_node are hidden from the form, being none of the user's business."""
    layer = ae_with_project.layers["links"][0]

    for field_name in ("a_node", "b_node"):
        assert layer.editorWidgetSetup(layer.fields().indexOf(field_name)).type() == "Hidden"


def test_link_modes_are_presented_as_values_from_the_modes_table(ae_with_project):
    """The modes field offers every combination of the project's modes, sorted and consistently spelled."""
    layer = ae_with_project.layers["links"][0]
    items = _value_map_items(layer, "modes")
    values = [value for _, value in items]

    # Every combination of the five modes, and this project spells all of its own the same way
    assert len(items) == 31
    assert values == sorted(values, key=lambda value: (value.casefold(), value))
    assert all(list(value) == sorted(value, key=lambda mode_id: (mode_id.casefold(), mode_id)) for value in values)
    assert dict(items)["bcMTt"] == "bcMTt"
    assert all(label == value for label, value in items)


def test_modes_a_project_already_uses_are_offered_as_they_are_stored(pt_no_feed):
    """Anything missing from the map is shown by QGIS in parentheses, which reads as an error."""
    layer = pt_no_feed.layers["links"][0]
    values = [value for _, value in _value_map_items(layer, "modes")]

    with pt_no_feed.project.db_connection as conn:
        in_use = [row[0] for row in conn.execute("SELECT DISTINCT modes FROM links").fetchall()]

    assert "cwbt" in in_use, "the fixture no longer holds a combination in its own order"
    assert set(in_use) <= set(values)


def test_link_types_are_presented_as_values_from_the_link_types_table(ae_with_project):
    """The link_type field offers the project's link types by name, without their ids."""
    layer = ae_with_project.layers["links"][0]
    items = _value_map_items(layer, "link_type")

    # The link type itself, with nothing appended - the id it carries is of no use here
    assert items == [("centroid_connector", "centroid_connector"), ("default", "default")]


def test_link_type_defaults_to_the_default_link_type(ae_with_project):
    """A new link starts on the 'default' link type."""
    layer = ae_with_project.layers["links"][0]
    field_index = layer.fields().indexOf("link_type")
    default = layer.defaultValueDefinition(field_index)

    assert default.expression() == "'default'"
    assert not default.applyOnUpdate()
    assert layer.defaultValue(field_index) == "default"


def test_modes_and_link_type_offer_the_previously_used_value(ae_with_project):
    """Only modes and link_type repeat the last value used; an id or a name never would."""
    layer = ae_with_project.layers["links"][0]
    config = layer.editFormConfig()

    assert config.reuseLastValue(layer.fields().indexOf("modes"))
    assert config.reuseLastValue(layer.fields().indexOf("link_type"))
    # Only the two fields worth repeating - a link id or a name carried over would be wrong
    assert not config.reuseLastValue(layer.fields().indexOf("link_id"))
    assert not config.reuseLastValue(layer.fields().indexOf("name"))


def test_link_type_cannot_be_left_empty(ae_with_project):
    """link_type carries a hard not-null constraint, so a link cannot be saved without one."""
    layer = ae_with_project.layers["links"][0]
    field_index = layer.fields().indexOf("link_type")
    not_null = QgsFieldConstraints.Constraint.ConstraintNotNull

    assert layer.fieldConstraints(field_index) & not_null
    assert (
        layer.fieldConstraintsAndStrength(field_index)[not_null]
        == QgsFieldConstraints.ConstraintStrength.ConstraintStrengthHard
    )

from qaequilibrae.modules.style_loader.editor_styles import _mode_combinations


def _value_map_items(layer, field_name):
    setup = layer.editorWidgetSetup(layer.fields().indexOf(field_name))
    assert setup.type() == "ValueMap"
    return [next(iter(item.items())) for item in setup.config()["map"]]


def _value_map(layer, field_name):
    return dict(_value_map_items(layer, field_name))


def test_mode_combinations_with_a_single_mode():
    assert _mode_combinations(["c"]) == [("c", "c")]


def test_link_identifiers_default_to_the_next_available_values(ae_with_project):
    layer = ae_with_project.layers["links"][0]

    for field_name in ("ogc_fid", "link_id"):
        field_index = layer.fields().indexOf(field_name)
        default = layer.defaultValueDefinition(field_index)

        assert default.expression() == f'coalesce(maximum("{field_name}"), 0) + 1'
        assert not default.applyOnUpdate()
        assert layer.defaultValue(field_index) == 77


def test_link_modes_are_presented_as_values_from_the_modes_table(ae_with_project):
    layer = ae_with_project.layers["links"][0]
    items = _value_map_items(layer, "modes")
    values = [value for _, value in items]

    assert len(items) == 31
    assert values == sorted(values, key=lambda value: (value.casefold(), value))
    assert all(list(value) == sorted(value, key=lambda mode_id: (mode_id.casefold(), mode_id)) for value in values)
    assert dict(items)["bcMTt"] == "bcMTt"
    assert all(label == value for label, value in items)


def test_link_types_are_presented_as_values_from_the_link_types_table(ae_with_project):
    layer = ae_with_project.layers["links"][0]

    assert _value_map(layer, "link_type") == {
        "centroid_connector (z)": "centroid_connector",
        "default (y)": "default",
    }

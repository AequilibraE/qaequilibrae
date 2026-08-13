from itertools import combinations

from qgis.core import QgsDefaultValue, QgsEditorWidgetSetup, QgsFieldConstraints, QgsVectorLayer

PREFERRED_LINK_TYPE = "default"


def load_editor_styles(layer: QgsVectorLayer, layer_name: str, project) -> None:
    """Configures the attribute forms used while digitizing the model."""
    name = layer_name.lower()
    if name == "links":
        _load_link_styles(layer, project)
    elif name == "zones":
        _load_zone_styles(layer)


def _load_zone_styles(layer: QgsVectorLayer) -> None:
    """Fills in the ids of a new zone, which is all a zone needs before it can be saved.

    The rest of what a zone carries - its name, and whatever the model added alongside it - is
    the user's to fill in, and so is the zone id whenever a numbering of their own is in use.
    """
    _set_next_id_default(layer, "ogc_fid")
    _set_next_id_default(layer, "zone_id")


def _load_link_styles(layer: QgsVectorLayer, project) -> None:
    _set_next_id_default(layer, "ogc_fid")
    _set_next_id_default(layer, "link_id")

    # The database rewrites both node ids from the link endpoints right after the insert, so these
    # are placeholders that only need to get past the insert - never something to fill in by hand.
    for field_name in ("a_node", "b_node"):
        _set_default(layer, field_name, "0")
        _hide_field(layer, field_name)

    with project.db_connection as conn:
        mode_ids = [row[0] for row in conn.execute("SELECT mode_id FROM modes").fetchall()]
        modes_in_use = [row[0] for row in conn.execute("SELECT DISTINCT modes FROM links").fetchall()]
        link_types = [
            row[0]
            for row in conn.execute(
                "SELECT link_type FROM link_types ORDER BY link_type COLLATE NOCASE, link_type"
            ).fetchall()
        ]

    _set_value_map(layer, "modes", _mode_combinations(mode_ids, modes_in_use))
    _set_value_map(layer, "link_type", [(link_type, link_type) for link_type in link_types])
    _require_link_type(layer, link_types)

    # Links get digitized in runs that mostly share these two, so the form offers the previous
    # choice rather than asking for it again. QGIS only remembers it for the session, which
    # leaves the very first link of each session on the defaults set above.
    _reuse_last_value(layer, ("modes", "link_type"))


def _reuse_last_value(layer: QgsVectorLayer, field_names: tuple[str, ...]) -> None:
    config = layer.editFormConfig()
    for field_name in field_names:
        field_index = layer.fields().indexOf(field_name)
        if field_index < 0:
            continue

        config.setReuseLastValue(field_index, True)

    layer.setEditFormConfig(config)


def _require_link_type(layer: QgsVectorLayer, link_types: list[str]) -> None:
    """A link with no link type is refused by the database triggers, so the form never offers one."""
    if not link_types:
        return

    link_type = PREFERRED_LINK_TYPE if PREFERRED_LINK_TYPE in link_types else link_types[0]
    escaped = link_type.replace("'", "''")
    _set_default(layer, "link_type", f"'{escaped}'")
    _set_not_null(layer, "link_type")


def _set_next_id_default(layer: QgsVectorLayer, field_name: str) -> None:
    _set_default(layer, field_name, f'coalesce(maximum("{field_name}"), 0) + 1')


def _set_default(layer: QgsVectorLayer, field_name: str, expression: str) -> None:
    field_index = layer.fields().indexOf(field_name)
    if field_index < 0:
        return

    layer.setDefaultValueDefinition(field_index, QgsDefaultValue(expression, False))


def _set_not_null(layer: QgsVectorLayer, field_name: str) -> None:
    field_index = layer.fields().indexOf(field_name)
    if field_index < 0:
        return

    layer.setFieldConstraint(
        field_index,
        QgsFieldConstraints.Constraint.ConstraintNotNull,
        QgsFieldConstraints.ConstraintStrength.ConstraintStrengthHard,
    )


def _set_value_map(layer: QgsVectorLayer, field_name: str, entries: list[tuple[str, str]]) -> None:
    _set_editor_widget(
        layer,
        field_name,
        QgsEditorWidgetSetup("ValueMap", {"map": [{label: value} for label, value in entries]}),
    )


def _hide_field(layer: QgsVectorLayer, field_name: str) -> None:
    _set_editor_widget(layer, field_name, QgsEditorWidgetSetup("Hidden", {}))


def _set_editor_widget(layer: QgsVectorLayer, field_name: str, setup: QgsEditorWidgetSetup) -> None:
    field_index = layer.fields().indexOf(field_name)
    if field_index < 0:
        return

    layer.setEditorWidgetSetup(field_index, setup)


def _mode_combinations(mode_ids: list[str], modes_in_use: list[str] = ()) -> list[tuple[str, str]]:
    """Every combination of the project's modes, plus the ones the links already carry.

    A combination is spelled in one order here, but a link may hold its modes in any order at
    all - `cwbt` is what an OSM import writes for a network AequilibraE would offer as `bctw`.
    QGIS shows a value its map has no entry for wrapped in parentheses, so what is already in
    use goes in exactly as stored, and nothing in the layer reads as an unknown value.
    """
    ordered_modes = sorted(mode_ids, key=lambda mode_id: (mode_id.casefold(), mode_id))
    entries = set()
    for size in range(1, len(ordered_modes) + 1):
        for selection in combinations(ordered_modes, size):
            entries.add("".join(selection))

    entries.update(modes for modes in modes_in_use if modes)

    return sorted(((modes, modes) for modes in entries), key=lambda entry: (entry[1].casefold(), entry[1]))

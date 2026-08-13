from itertools import combinations

from qgis.core import QgsDefaultValue, QgsEditorWidgetSetup, QgsVectorLayer


def load_editor_styles(layer: QgsVectorLayer, layer_name: str, project) -> None:
    """Configures the attribute form used while digitizing network links."""
    if layer_name.lower() != "links":
        return

    _set_next_id_default(layer, "ogc_fid")
    _set_next_id_default(layer, "link_id")

    with project.db_connection as conn:
        modes = conn.execute(
            "SELECT mode_name, mode_id FROM modes ORDER BY mode_name COLLATE NOCASE, mode_id"
        ).fetchall()
        link_types = conn.execute(
            "SELECT link_type, link_type_id FROM link_types ORDER BY link_type COLLATE NOCASE, link_type_id"
        ).fetchall()

    _set_value_map(layer, "modes", _mode_combinations(modes))
    _set_value_map(
        layer,
        "link_type",
        [(f"{link_type} ({link_type_id})", link_type) for link_type, link_type_id in link_types],
    )


def _set_next_id_default(layer: QgsVectorLayer, field_name: str) -> None:
    field_index = layer.fields().indexOf(field_name)
    if field_index < 0:
        return

    expression = f'coalesce(maximum("{field_name}"), 0) + 1'
    layer.setDefaultValueDefinition(field_index, QgsDefaultValue(expression, False))


def _set_value_map(layer: QgsVectorLayer, field_name: str, entries: list[tuple[str, str]]) -> None:
    field_index = layer.fields().indexOf(field_name)
    if field_index < 0:
        return

    layer.setEditorWidgetSetup(
        field_index,
        QgsEditorWidgetSetup("ValueMap", {"map": [{label: value} for label, value in entries]}),
    )


def _mode_combinations(modes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    ordered_modes = sorted(modes, key=lambda mode: (mode[1].casefold(), mode[1]))
    entries = []
    for size in range(1, len(ordered_modes) + 1):
        for selection in combinations(ordered_modes, size):
            mode_names = " + ".join(mode_name for mode_name, _ in selection)
            mode_ids = "".join(mode_id for _, mode_id in selection)
            entries.append((f"{mode_names} ({mode_ids})", mode_ids))

    return sorted(entries, key=lambda entry: (entry[1].casefold(), entry[1]))

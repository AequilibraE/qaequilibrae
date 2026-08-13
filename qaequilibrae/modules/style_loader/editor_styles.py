from itertools import combinations

from qgis.core import QgsDefaultValue, QgsEditorWidgetSetup, QgsVectorLayer


def load_editor_styles(layer: QgsVectorLayer, layer_name: str, project) -> None:
    """Configures the attribute form used while digitizing network links."""
    if layer_name.lower() != "links":
        return

    _set_next_id_default(layer, "ogc_fid")
    _set_next_id_default(layer, "link_id")
    _set_default(layer, "a_node", "0")
    _set_default(layer, "b_node", "0")

    with project.db_connection as conn:
        mode_ids = [row[0] for row in conn.execute("SELECT mode_id FROM modes").fetchall()]
        link_types = conn.execute(
            "SELECT link_type, link_type_id FROM link_types ORDER BY link_type COLLATE NOCASE, link_type_id"
        ).fetchall()

    _set_value_map(layer, "modes", _mode_combinations(mode_ids))
    _set_value_map(
        layer,
        "link_type",
        [(f"{link_type} ({link_type_id})", link_type) for link_type, link_type_id in link_types],
    )


def _set_next_id_default(layer: QgsVectorLayer, field_name: str) -> None:
    _set_default(layer, field_name, f'coalesce(maximum("{field_name}"), 0) + 1')


def _set_default(layer: QgsVectorLayer, field_name: str, expression: str) -> None:
    field_index = layer.fields().indexOf(field_name)
    if field_index < 0:
        return

    layer.setDefaultValueDefinition(field_index, QgsDefaultValue(expression, False))


def _set_value_map(layer: QgsVectorLayer, field_name: str, entries: list[tuple[str, str]]) -> None:
    field_index = layer.fields().indexOf(field_name)
    if field_index < 0:
        return

    layer.setEditorWidgetSetup(
        field_index,
        QgsEditorWidgetSetup("ValueMap", {"map": [{label: value} for label, value in entries]}),
    )


def _mode_combinations(mode_ids: list[str]) -> list[tuple[str, str]]:
    ordered_modes = sorted(mode_ids, key=lambda mode_id: (mode_id.casefold(), mode_id))
    entries = []
    for size in range(1, len(ordered_modes) + 1):
        for selection in combinations(ordered_modes, size):
            mode_combination = "".join(selection)
            entries.append((mode_combination, mode_combination))

    return sorted(entries, key=lambda entry: (entry[1].casefold(), entry[1]))

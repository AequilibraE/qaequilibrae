import pytest

from qaequilibrae.modules.network import AddLinkTypeDialog, AddModeDialog
from qaequilibrae.modules.processing_provider.provider import Provider


def _column(table, header):
    """The columns follow the project's own table, so they are found by name rather than counted."""
    headers = [table.horizontalHeaderItem(column).text() for column in range(table.columnCount())]
    assert header in headers
    return headers.index(header)


def _value_map(layer, field_name):
    setup = layer.editorWidgetSetup(layer.fields().indexOf(field_name))
    return [value for item in setup.config()["map"] for value in item.values()]


def test_the_tools_are_in_the_data_group_of_the_toolbox(qgis_app):
    provider = Provider()
    provider.refreshAlgorithms()

    groups = {algorithm.name(): algorithm.groupId() for algorithm in provider.algorithms()}

    assert groups["add_link_type"] == "data"
    assert groups["add_mode"] == "data"


def test_add_mode_lists_the_modes_already_in_the_project(ae_with_project):
    dialog = AddModeDialog(ae_with_project)

    modes = ae_with_project.project.network.modes.all_modes()
    identifiers = _column(dialog.tbl_existing, "mode_id")
    assert dialog.tbl_existing.rowCount() == len(modes)
    assert [dialog.tbl_existing.item(row, identifiers).text() for row in range(len(modes))] == sorted(modes)

    # The identifier the dialog offers has to be one the project does not have yet
    assert dialog.txt_id.text() not in modes


def test_add_mode(ae_with_project):
    dialog = AddModeDialog(ae_with_project)
    dialog.txt_name.setText("flying_car")
    dialog.txt_description.setText("Cars that fly")
    dialog.dsb_pce.setValue(2.5)
    dialog.dsb_vot.setValue(30.0)
    dialog.dsb_ppv.setValue(1.5)

    mode_id = dialog.txt_id.text()
    dialog.add_record()

    modes = ae_with_project.project.network.modes.all_modes()
    assert mode_id in modes

    mode = modes[mode_id]
    assert mode.mode_name == "flying_car"
    assert mode.description == "Cars that fly"
    assert (mode.pce, mode.vot, mode.ppv) == (2.5, 30.0, 1.5)

    # The form is ready for the next one, and the new mode is listed
    assert dialog.txt_name.text() == ""
    assert dialog.txt_id.text() not in modes
    assert dialog.tbl_existing.rowCount() == len(modes)


def test_add_mode_without_a_description(ae_with_project):
    dialog = AddModeDialog(ae_with_project)
    dialog.txt_name.setText("scooter")

    mode_id = dialog.txt_id.text()
    dialog.add_record()

    with ae_with_project.project.db_connection as conn:
        description = conn.execute(f"select description from modes where mode_id='{mode_id}'").fetchone()[0]

    assert description is None


@pytest.mark.parametrize(
    ("mode_id", "name"),
    [
        ("", "flying_car"),
        ("1", "flying_car"),
        ("c", "flying_car"),
        ("k", ""),
        ("k", "flying car"),
        ("k", "flying-car"),
        ("k", "car"),
        ("k", "CAR"),
    ],
)
def test_add_mode_refuses_what_the_project_cannot_take(ae_with_project, mode_id, name):
    dialog = AddModeDialog(ae_with_project)
    before = set(ae_with_project.project.network.modes.all_modes())

    dialog.txt_id.setText(mode_id)
    dialog.txt_name.setText(name)
    dialog.add_record()

    assert dialog.lbl_feedback.text() != ""
    assert set(ae_with_project.project.network.modes.all_modes()) == before


def test_add_link_type_lists_the_link_types_already_in_the_project(ae_with_project):
    dialog = AddLinkTypeDialog(ae_with_project)

    link_types = ae_with_project.project.network.link_types.all_types()
    identifiers = _column(dialog.tbl_existing, "link_type_id")
    assert dialog.tbl_existing.rowCount() == len(link_types)
    assert [dialog.tbl_existing.item(row, identifiers).text() for row in range(len(link_types))] == sorted(link_types)

    assert dialog.txt_id.text() not in link_types


def test_add_link_type(ae_with_project):
    dialog = AddLinkTypeDialog(ae_with_project)
    dialog.txt_name.setText("arterial")
    dialog.txt_description.setText("Streets like AequilibraE Avenue")
    dialog.sb_lanes.setValue(3)
    dialog.sb_lane_capacity.setValue(1100)

    link_type_id = dialog.txt_id.text()
    dialog.add_record()

    link_types = ae_with_project.project.network.link_types.all_types()
    assert link_type_id in link_types

    link_type = link_types[link_type_id]
    assert link_type.link_type == "arterial"
    assert link_type.description == "Streets like AequilibraE Avenue"
    assert (link_type.lanes, link_type.lane_capacity) == (3, 1100)

    assert dialog.txt_name.text() == ""
    assert dialog.tbl_existing.rowCount() == len(link_types)


def test_add_link_type_leaves_the_numbers_reading_not_set_empty(ae_with_project):
    dialog = AddLinkTypeDialog(ae_with_project)
    dialog.txt_name.setText("arterial")

    link_type_id = dialog.txt_id.text()
    dialog.add_record()

    with ae_with_project.project.db_connection as conn:
        stored = conn.execute(
            f"select description, lanes, lane_capacity from link_types where link_type_id='{link_type_id}'"
        ).fetchone()

    assert stored == (None, None, None)


def test_the_form_only_offers_the_columns_the_project_has(ae_with_project):
    """The Sioux Falls model has no speed column, and writing to one that is missing goes nowhere."""
    dialog = AddLinkTypeDialog(ae_with_project)

    assert dialog.dsb_speed.isHidden() and dialog.lbl_speed.isHidden()
    assert not dialog.sb_lanes.isHidden()


def test_add_link_type_with_a_speed(pt_no_feed):
    dialog = AddLinkTypeDialog(pt_no_feed)
    assert not dialog.dsb_speed.isHidden()

    dialog.txt_name.setText("arterial")
    dialog.dsb_speed.setValue(13.5)

    link_type_id = dialog.txt_id.text()
    dialog.add_record()

    assert pt_no_feed.project.network.link_types.all_types()[link_type_id].speed == 13.5


@pytest.mark.parametrize(
    ("link_type_id", "name"),
    [
        ("", "arterial"),
        ("2", "arterial"),
        ("y", "arterial"),
        ("a", ""),
        ("a", "urban arterial"),
        ("a", "default"),
        ("a", "DEFAULT"),
    ],
)
def test_add_link_type_refuses_what_the_project_cannot_take(ae_with_project, link_type_id, name):
    dialog = AddLinkTypeDialog(ae_with_project)
    before = set(ae_with_project.project.network.link_types.all_types())

    dialog.txt_id.setText(link_type_id)
    dialog.txt_name.setText(name)
    dialog.add_record()

    assert dialog.lbl_feedback.text() != ""
    assert set(ae_with_project.project.network.link_types.all_types()) == before


def test_a_link_type_that_cannot_be_saved_does_not_hold_on_to_its_identifier(ae_with_project, monkeypatch):
    """A link type only reaches the project when it saves, but new() lists it before that."""
    from aequilibrae.project.network.link_type import LinkType

    def refuse_to_save(self):
        raise ValueError("the database said no")

    monkeypatch.setattr(LinkType, "save", refuse_to_save)

    dialog = AddLinkTypeDialog(ae_with_project)
    dialog.txt_name.setText("arterial")

    link_type_id = dialog.txt_id.text()
    dialog.add_record()

    assert dialog.lbl_feedback.text() != ""
    assert link_type_id not in ae_with_project.project.network.link_types.all_types()


def test_the_new_mode_reaches_the_form_used_to_digitize_links(ae_with_project):
    dialog = AddModeDialog(ae_with_project)
    dialog.txt_name.setText("scooter")

    mode_id = dialog.txt_id.text()
    dialog.add_record()

    assert mode_id in _value_map(ae_with_project.layers["links"][0], "modes")


def test_the_new_link_type_reaches_the_form_used_to_digitize_links(ae_with_project):
    dialog = AddLinkTypeDialog(ae_with_project)
    dialog.txt_name.setText("arterial")

    dialog.add_record()

    assert "arterial" in _value_map(ae_with_project.layers["links"][0], "link_type")

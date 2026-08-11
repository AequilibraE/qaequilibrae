from os.path import join
import pytest
import sys

from aequilibrae import Project
from qgis.PyQt import QtWidgets
from qgis.core import QgsProject

from qaequilibrae.modules.project_procedures.creates_transponet_dialog import CreatesTranspoNetDialog
from qaequilibrae.modules.project_procedures.creates_transponet_procedure import CreatesTranspoNetProcedure
from .utilities import load_test_layer

pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Running on Windows")

# The standard AequilibraE link layer, minus a_node/b_node/distance, which the project computes on its own
link_standard_fields = ["link_id", "direction", "modes", "link_type", "name", "speed_ab", "speed_ba",
                        "travel_time_ab", "travel_time_ba", "capacity_ab", "capacity_ba"]  # fmt: skip
node_standard_fields = ["node_id", "is_centroid"]

# The ones AequilibraE requires, which are the only ones taken from the layer by default
link_fields_from_layer = ["link_id", "direction", "modes", "link_type"]


def fields_in_table(table):
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def checkbox_for(table, field):
    row = fields_in_table(table).index(field)
    return table.cellWidget(row, 1).findChildren(QtWidgets.QCheckBox)[0]


def set_source_field(table, field, source):
    row = fields_in_table(table).index(field)
    combobox = table.cellWidget(row, 2).findChildren(QtWidgets.QComboBox)[0]
    combobox.setCurrentIndex(combobox.findText(source))


def map_standard_fields(dialog):
    for field in link_fields_from_layer:
        set_source_field(dialog.table_link_fields, field, field)

    for field in node_standard_fields:
        set_source_field(dialog.table_node_fields, field, field)


def test_dialog_only_offers_standard_fields(ae, folder_path):
    load_test_layer(folder_path, "node")
    load_test_layer(folder_path, "link")

    dialog = CreatesTranspoNetDialog(ae)

    assert fields_in_table(dialog.table_link_fields) == link_standard_fields
    assert fields_in_table(dialog.table_node_fields) == node_standard_fields

    # Fields computed by the project's triggers cannot be brought from the layer
    for field in ["a_node", "b_node", "distance"]:
        assert field not in fields_in_table(dialog.table_available_link_fields)

    # Any other field from the layer is up to the user to bring in
    for field in ["matrix_ab", "matrix_ba", "matrix_tot"]:
        assert field in fields_in_table(dialog.table_available_link_fields)

    # The fields AequilibraE requires come from the layer, and only link_id can be initialized instead
    assert checkbox_for(dialog.table_link_fields, "link_id").isEnabled()
    for field in ["direction", "modes", "link_type"]:
        assert not checkbox_for(dialog.table_link_fields, field).isEnabled()
    for field in node_standard_fields:
        assert not checkbox_for(dialog.table_node_fields, field).isEnabled()

    for field in link_fields_from_layer:
        assert not checkbox_for(dialog.table_link_fields, field).isChecked()

    # The remaining standard fields start out initialized, but the user can bring them from the layer
    for field in ["name", "speed_ab", "travel_time_ba", "capacity_ab"]:
        assert checkbox_for(dialog.table_link_fields, field).isChecked()
        assert checkbox_for(dialog.table_link_fields, field).isEnabled()


def test_dialog(ae, folder_path):
    load_test_layer(folder_path, "node")
    load_test_layer(folder_path, "link")

    dialog = CreatesTranspoNetDialog(ae)
    dialog.project_destination.setText(folder_path)

    map_standard_fields(dialog)

    # A standard field that starts out initialized can still be brought from the layer
    checkbox_for(dialog.table_link_fields, "name").setChecked(False)
    set_source_field(dialog.table_link_fields, "name", "name")

    dialog.create_net()

    # Test assertions
    project = Project()
    project.open(dialog.worker_thread.proj_folder)

    project_links = project.network.links.data
    assert project_links.shape[0] == 5
    assert sorted(project_links["link_id"].tolist()) == [1, 2, 3, 4, 5]
    assert "fifth link" in project_links["name"].tolist()

    # Standard fields left initialized are simply empty
    assert project_links["speed_ab"].isna().all()

    project_nodes = project.network.nodes.data
    assert project_nodes.shape[0] == 4
    assert project_nodes[project_nodes["is_centroid"] == 1].shape[0] == 2

    link_types = project.network.link_types
    assert "a" in link_types.all_types().keys()

    modes = project.network.modes
    for mode in ["a", "r", "x"]:
        assert mode in modes.all_modes().keys()


def test_dialog_bringing_extra_field_from_layer(ae, folder_path):
    load_test_layer(folder_path, "node")
    load_test_layer(folder_path, "link")

    dialog = CreatesTranspoNetDialog(ae)
    dialog.project_destination.setText(folder_path)

    map_standard_fields(dialog)

    # Fields that are not part of the standard layer are brought from the layer by the user
    available = dialog.table_available_link_fields
    available.selectRow(fields_in_table(available).index("matrix_ab"))
    dialog.but_adds_to_links.click()

    assert "matrix_ab" in fields_in_table(dialog.table_link_fields)

    dialog.create_net()

    project = Project()
    project.open(dialog.worker_thread.proj_folder)

    project_links = project.network.links.data
    assert sorted(project_links["matrix_ab"].tolist()) == [17, 19, 32, 42, 50]


def test_dialog_initializing_link_id(ae, folder_path):
    load_test_layer(folder_path, "node")
    load_test_layer(folder_path, "link")

    dialog = CreatesTranspoNetDialog(ae)
    dialog.project_destination.setText(folder_path)

    map_standard_fields(dialog)

    # We let QAequilibraE number the links for us
    checkbox_for(dialog.table_link_fields, "link_id").setChecked(True)

    dialog.create_net()

    assert dialog.link_fields["link_id"] == -1

    project = Project()
    project.open(dialog.worker_thread.proj_folder)

    project_links = project.network.links.data
    assert sorted(project_links["link_id"].tolist()) == [1, 2, 3, 4, 5]


def test_procedure(ae, folder_path):
    load_test_layer(folder_path, "node")
    load_test_layer(folder_path, "link")

    nodes = QgsProject.instance().mapLayersByName("node")[0]
    links = QgsProject.instance().mapLayersByName("link")[0]

    links_fields = {"link_id": 7, "direction": 2, "modes": 4, "link_type": 5, "name": 6, "speed_ab": -1}
    nodes_fields = {"node_id": 0, "is_centroid": 1}

    proj_folder = join(folder_path, "project")
    parent = CreatesTranspoNetDialog(ae)
    dialog = CreatesTranspoNetProcedure(parent, proj_folder, nodes, nodes_fields, links, links_fields)

    dialog.doWork()

    project = Project()
    project.open(proj_folder)

    project_links = project.network.links.data
    assert project_links.shape[0] == 5
    assert sorted(project_links["link_id"].tolist()) == [1, 2, 3, 4, 5]
    assert "fifth link" in project_links["name"].tolist()
    assert project_links["speed_ab"].isna().all()

    project_nodes = project.network.nodes.data
    assert project_nodes.shape[0] == 4
    assert project_nodes[project_nodes["is_centroid"] == 1].shape[0] == 2

    link_types = project.network.link_types
    assert "a" in link_types.all_types().keys()

    modes = project.network.modes
    for mode in ["a", "r", "x"]:
        assert mode in modes.all_modes().keys()


def test_procedure_without_link_id(ae, folder_path):
    load_test_layer(folder_path, "node")
    load_test_layer(folder_path, "link")

    nodes = QgsProject.instance().mapLayersByName("node")[0]
    links = QgsProject.instance().mapLayersByName("link")[0]

    links_fields = {"link_id": -1, "direction": 2, "modes": 4, "link_type": 5}
    nodes_fields = {"node_id": 0, "is_centroid": 1}

    proj_folder = join(folder_path, "project")
    parent = CreatesTranspoNetDialog(ae)
    dialog = CreatesTranspoNetProcedure(parent, proj_folder, nodes, nodes_fields, links, links_fields)

    dialog.doWork()

    project = Project()
    project.open(proj_folder)

    project_links = project.network.links.data
    assert project_links.shape[0] == 5
    assert sorted(project_links["link_id"].tolist()) == [1, 2, 3, 4, 5]

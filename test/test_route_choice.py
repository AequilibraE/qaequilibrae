import sqlite3
from os import listdir
from os.path import join
from pathlib import Path

import numpy as np
import pytest
from PyQt5.QtCore import Qt
from qgis.core import QgsProject

from qaequilibrae.modules.paths_procedures.execute_single_dialog import ExecuteSingleDialog
from qaequilibrae.modules.paths_procedures.route_choice_dialog import RouteChoiceDialog
from .utilities import create_matrix


@pytest.mark.parametrize("cob_field", ["distance", "free_flow_time"])
def test_execute_single(sf_project, qtbot, cob_field):
    dialog = RouteChoiceDialog(sf_project)

    # Choice set generation
    dialog.max_routes.setText("3")

    # Route choice
    dialog.cob_net_field.setCurrentText(cob_field)
    dialog.ln_parameter.setText("0.00011")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)

    dialog.ln_psl.setText("1.1")

    # Graph configuration
    dialog.chb_check_centroids.setChecked(False)

    # Workflow
    dialog.node_from.setText("1")
    dialog.node_to.setText("15")
    dialog.ln_demand.setText("1.0")
    qtbot.mouseClick(dialog.but_visualize, Qt.LeftButton)

    dialog.exit_procedure()

    layers = list(QgsProject.instance().mapLayers().values())
    layers = [lyr.name() for lyr in layers]
    assert "route_set-1-15" in layers

    # Check if dialog was closed
    assert not dialog.isVisible()


def test_execute_single_dialog(coquimbo_project, qtbot, qgis_iface):
    project = coquimbo_project.project
    project.network.build_graphs(modes=["c"])

    graph = project.network.graphs["c"]
    graph.network = graph.network.assign(__utility__=graph.network.distance * 0.011)
    graph.prepare_graph(graph.centroids)
    graph.set_graph("__utility__")
    graph.set_blocked_centroid_flows(False)

    params = {
        "algorithm": "bfsle",
        "matrix": 1.0,
        "node_from": "77011",
        "node_to": "74089",
        "kwargs": {
            "max_routes": 3,
            "beta": 1.1,
        },
    }

    dialog = ExecuteSingleDialog(qgis_iface, graph, coquimbo_project.layers["links"][0], params)
    dialog.debouncer.delay_ms = 100
    dialog.node_from.clear()
    qtbot.mouseClick(dialog.node_from, Qt.LeftButton)
    qtbot.keyClicks(dialog.node_from, "71645")
    qtbot.wait(200)
    dialog.node_to.clear()
    qtbot.mouseClick(dialog.node_to, Qt.LeftButton)
    qtbot.keyClicks(dialog.node_to, "79385")
    qtbot.wait(200)

    dialog.exit_procedure()

    layers = list(QgsProject.instance().mapLayers().values())
    layers = [lyr.name() for lyr in layers]
    assert "route_set-71645-79385" in layers


@pytest.mark.parametrize("save", [True, False])
def test_assign_and_save(ae_with_project, qtbot, save):
    dialog = RouteChoiceDialog(ae_with_project)

    # Choice set generation
    dialog.max_routes.setText("3")

    # Route choice
    dialog.cob_net_field.setCurrentText("distance")
    dialog.ln_parameter.setText("0.01")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)

    dialog.ln_psl.setText("1.1")

    # Graph configuration
    dialog.chb_check_centroids.setChecked(False)

    dialog.chb_save_choice_set.setChecked(save)
    dialog.cob_matrices.setCurrentText("demand.aem")
    dialog.ln_rc_output.setText("route_choice")
    qtbot.mouseClick(dialog.but_perform_assig, Qt.LeftButton)

    pth = Path(dialog.project.project_base_path)
    conn = sqlite3.connect(pth / "results_database.sqlite")
    results = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    assert "route_choice_uncompressed" in results

    if save:
        counter = 0
        rc_folder = listdir(join(dialog.project.project_base_path, "route_choice"))
        for folder in rc_folder:
            if "origin id=" in folder:
                counter += 1

        assert counter == 24

        messagebar = ae_with_project.iface.messageBar()
        assert "Success:Route choice sets saved to" in messagebar.messages[3][0]


def test_build_and_save(ae_with_project, qtbot):
    dialog = RouteChoiceDialog(ae_with_project)

    dialog.matrices.reload()
    dialog.list_matrices()

    # Choice set generation
    dialog.max_routes.setText("3")

    # Route choice
    dialog.cob_net_field.setCurrentText("distance")
    dialog.ln_parameter.setText("0.01")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)

    dialog.ln_psl.setText("1.1")

    # Graph configuration
    dialog.chb_check_centroids.setChecked(False)

    dialog.cob_matrices.setCurrentText("demand.aem")
    qtbot.mouseClick(dialog.but_build_and_save, Qt.LeftButton)

    counter = 0
    rc_folder = listdir(join(dialog.project.project_base_path, "route_choice"))
    for folder in rc_folder:
        if "origin id=" in folder:
            counter += 1

    assert counter == 24

    messagebar = ae_with_project.iface.messageBar()
    assert "Success:Route choice sets saved to" in messagebar.messages[3][0]


def create_dialog_with_matrix(project):
    pth = join(project.project.project_base_path, "matrices/demand.aem")
    create_matrix(np.arange(1, 134), pth)

    matrices = project.project.matrices
    matrices.update_database()
    matrices.reload()

    return RouteChoiceDialog(project)


def test_sub_area_analysis(coquimbo_project, qtbot):
    dialog = create_dialog_with_matrix(coquimbo_project)

    # Select zones
    dialog.qgis_project.load_layer_by_name("zones")
    exp = '"zone_id" IN (29, 30, 31, 32, 33, 34, 37, 38, 39, 40, 49, 50, 51, 52, 57, 58, 59, 60)'
    zones = dialog.qgis_project.layers["zones"][0]
    zones.selectByExpression(exp)

    dialog.matrices.reload()
    dialog.list_matrices()

    # Choice set generation
    dialog.max_routes.setText("3")
    dialog.cob_algo.setCurrentText("Link Penalization")
    dialog.penalty.setText("1.02")

    # Route choice
    dialog.cob_net_field.setCurrentText("distance")
    dialog.ln_parameter.setText("0.011")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)

    dialog.ln_psl.setText("1.1")

    # Graph configuration
    dialog.chb_check_centroids.setChecked(False)

    # Set sub-area analysis
    dialog.chb_set_sub_area.setChecked(True)
    dialog.chb_selected_zones.setChecked(True)

    # Execute workflow
    dialog.chb_save_choice_set.setChecked(True)
    dialog.cob_matrices.setCurrentText("b''")
    dialog.ln_rc_output.setText("route_choice_for_subarea")
    qtbot.mouseClick(dialog.but_perform_assig, Qt.LeftButton)

    pth = Path(dialog.project.project_base_path)
    conn = sqlite3.connect(pth / "results_database.sqlite")
    results = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    assert "route_choice_for_subarea_uncompressed" in results

    rc_folder = listdir(join(dialog.project.project_base_path, "route_choice"))
    assert "route_choice_for_subarea.parquet" in rc_folder


def test_select_link_analysis(coquimbo_project, qtbot):
    dialog = create_dialog_with_matrix(coquimbo_project)

    dialog.matrices.reload()
    dialog.list_matrices()

    # Choice set generation
    dialog.max_routes.setText("3")
    dialog.cob_algo.setCurrentText("BFSLE")
    dialog.penalty.setText("1.00")

    # Route choice
    dialog.cob_net_field.setCurrentText("distance")
    dialog.ln_parameter.setText("0.011")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)

    dialog.ln_psl.setText("1.1")

    # Graph configuration
    dialog.chb_check_centroids.setChecked(False)

    # Set select link analysis
    dialog.chb_set_select_link.setChecked(True)
    dialog.ln_qry_name.setText("sl1")
    dialog.ln_link_id.setText("7369")
    dialog.cob_direction.setCurrentText("AB")
    qtbot.mouseClick(dialog.but_add_qry, Qt.LeftButton)
    dialog.ln_link_id.setText("20983")
    dialog.cob_direction.setCurrentText("AB")
    qtbot.mouseClick(dialog.but_add_qry, Qt.LeftButton)
    qtbot.mouseClick(dialog.but_save_qry, Qt.LeftButton)
    dialog.ln_qry_name.setText("sl2")
    dialog.ln_link_id.setText("7369")
    dialog.cob_direction.setCurrentText("AB")
    qtbot.mouseClick(dialog.but_add_qry, Qt.LeftButton)
    qtbot.mouseClick(dialog.but_save_qry, Qt.LeftButton)
    dialog.ln_mat_name.setText("select_link_analysis")

    # Execute workflow
    dialog.chb_save_choice_set.setChecked(True)
    dialog.cob_matrices.setCurrentText("b''")
    qtbot.mouseClick(dialog.but_perform_assig, Qt.LeftButton)

    matrices = listdir(dialog.project.matrices.fldr)
    assert "select_link_analysis.omx" in matrices

    pth = Path(dialog.project.project_base_path)
    conn = sqlite3.connect(pth / "results_database.sqlite")
    results = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    assert "select_link_analysis_uncompressed" in results


# ### We add tests to capture the errors raised
# Cost function
@pytest.mark.parametrize("par", ["", "abc", "0,10", "  "])
def test_cost_function(coquimbo_project, qtbot, par):
    dialog = create_dialog_with_matrix(coquimbo_project)

    dialog.ln_parameter.setText(par)
    dialog.cob_net_field.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == "Input error:Check parameter value input"


# Cost function clean-up
def test_clean_cost_function(coquimbo_project, qtbot):
    dialog = create_dialog_with_matrix(coquimbo_project)

    dialog.ln_parameter.setText("0.11")
    dialog.cob_net_field.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)
    txt = "0.11 * distance"

    assert dialog.txt_cost_func.toPlainText() == txt

    dialog.ln_parameter.setText("0.50")
    dialog.cob_net_field.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)
    txt += " + 0.50 * distance"

    assert dialog.txt_cost_func.toPlainText() == txt

    dialog.ln_parameter.setText("-0.33")
    dialog.cob_net_field.setCurrentText("distance")
    qtbot.mouseClick(dialog.but_add_to_cost, Qt.LeftButton)
    txt += " - 0.33 * distance"

    assert dialog.txt_cost_func.toPlainText() == txt

    dialog.clear_cost_function()

    assert dialog.txt_cost_func.toPlainText() == ""


@pytest.mark.parametrize(
    "par,error",
    [("", "Missing query name"), ("sl1", "Query name already used"), ("sl2", "Please set a link selection")],
)
def test_query_name(coquimbo_project, par, error):
    dialog = create_dialog_with_matrix(coquimbo_project)

    dialog.select_links = {"sl1": [[(7369, 1), (20983, 1)]]}

    dialog.ln_qry_name.setText(par)
    if par != "sl2":
        dialog.ln_link_id.setText("7369")
        dialog.cob_direction.setCurrentText("AB")
        dialog.add_query()

    dialog.save_query()

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == f"Input error:{error}"


@pytest.mark.parametrize(
    "par,error",
    [
        ("", "Max. routes needs to be a positive integer value"),
        ("abc", "Max. routes needs to be a positive integer value"),
        ("1.3", "Max. routes needs to be a positive integer value"),
        ("0", "One of max. routes or max. depth has to be greater than 0"),
        ("-1", "Max. routes needs to be a positive integer value"),
    ],
)
def test_max_routes(coquimbo_project, par, error):
    dialog = create_dialog_with_matrix(coquimbo_project)

    depth = "0" if par == "0" else "1"
    dialog.max_depth.setText(depth)
    dialog.max_routes.setText(par)
    dialog.job = None

    dialog._validate_inputs()

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == f"Input error:{error}"


@pytest.mark.parametrize(
    "par,error",
    [
        ("", "Max. depth needs to be a positive integer value"),
        ("abc", "Max. depth needs to be a positive integer value"),
        ("1.3", "Max. depth needs to be a positive integer value"),
        ("0", "One of max. routes or max. depth has to be greater than 0"),
        ("-1", "Max. depth needs to be a positive integer value"),
    ],
)
def test_max_depth(coquimbo_project, par, error):
    dialog = create_dialog_with_matrix(coquimbo_project)

    routes = "0" if par == "0" else "1"
    dialog.max_depth.setText(par)
    dialog.max_routes.setText(routes)
    dialog.job = None

    dialog._validate_inputs()

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == f"Input error:{error}"


@pytest.mark.parametrize(
    "par,error",
    [
        ("", "Probability cutoff needs to be a positive float value"),
        ("abc", "Probability cutoff needs to be a positive float value"),
        ("1.3", "Probability cutoff assumes values between 0.0 and 1.0"),
        ("-0.5", "Probability cutoff needs to be a positive float value"),
    ],
)
def test_cutoff(coquimbo_project, par, error):
    dialog = create_dialog_with_matrix(coquimbo_project)

    dialog.max_routes.setText("1")
    dialog.max_depth.setText("1")
    dialog.ln_cutoff.setText(par)
    dialog.job = None

    dialog._validate_inputs()

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == f"Input error:{error}"


@pytest.mark.parametrize(
    "par,error",
    [
        ("", "Penalty needs to be a positive float value"),
        ("abc", "Penalty needs to be a positive float value"),
        ("1.0", "Penalty needs to be greater than 1.0 for BFSLE with Link Penalization"),
        ("-0.5", "Penalty needs to be a positive float value"),
    ],
)
def test_penalty(coquimbo_project, par, error):
    dialog = create_dialog_with_matrix(coquimbo_project)

    dialog.cob_algo.setCurrentText("BFSLE with Link Penalization")
    dialog.max_routes.setText("1")
    dialog.max_depth.setText("1")
    dialog.ln_cutoff.setText("0.5")
    dialog.penalty.setText(par)
    dialog.job = None

    dialog._validate_inputs()

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == f"Input error:{error}"


@pytest.mark.parametrize(
    "par,error",
    [
        ("", "PSL (beta) needs to be a positive float value"),
        ("abc", "PSL (beta) needs to be a positive float value"),
        ("-0.5", "PSL (beta) needs to be a positive float value"),
    ],
)
def test_psl_beta(coquimbo_project, par, error):
    dialog = create_dialog_with_matrix(coquimbo_project)

    dialog.max_routes.setText("1")
    dialog.max_depth.setText("1")
    dialog.ln_cutoff.setText("0.5")
    dialog.penalty.setText("1.0")
    dialog.ln_psl.setText(par)
    dialog.job = None

    dialog._validate_inputs()

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[1][0] == f"Input error:{error}"

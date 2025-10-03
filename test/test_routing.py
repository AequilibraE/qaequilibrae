import pytest
import qgis
from qgis.core import QgsProject

from qaequilibrae.modules.routing_procedures.tsp_dialog import TSPDialog
from qaequilibrae.modules.routing_procedures.tsp_procedure import TSPProcedure


@pytest.mark.parametrize("in_selection", [False, True])
def test_create_from_centroids(ae_with_project, in_selection):
    dialog = TSPDialog(ae_with_project)

    dialog.chb_block.setChecked(True)
    dialog.rdo_new_layer.setChecked(in_selection)
    dialog.close_window = True
    dialog.cob_minimize.setCurrentText("distance")

    dialog.run()

    if in_selection:
        layers = list(QgsProject.instance().mapLayers().values())
        names = [layer.name() for layer in layers]

        assert "TSP Solution" in names
        assert "TSP Stops" in names
    else:
        assert len(dialog.worker_thread.node_sequence) == 25

    ae_with_project.run_close_project()


@pytest.mark.parametrize("in_selection", [False, True])
def test_create_from_nodes(pt_project, in_selection):
    nodes = pt_project.layers["nodes"][0]
    node_selection = [74034, 74035, 74101]
    nodes.select([f.id() for f in nodes.getFeatures() if f["node_id"] in node_selection])

    dialog = TSPDialog(pt_project)
    dialog.rdo_centroids.setChecked(False)
    dialog.rdo_selected.setChecked(True)
    dialog.populate_node_source()
    dialog.rdo_new_layer.setChecked(in_selection)
    dialog.close_window = True
    dialog.cob_minimize.setCurrentText("distance")
    dialog.cob_start.setCurrentText("74034")

    dialog.run()

    if in_selection:
        layers = list(QgsProject.instance().mapLayers().values())
        names = [layer.name() for layer in layers]

        assert "TSP Solution" in names
        assert "TSP Stops" in names
    else:
        assert len(dialog.worker_thread.node_sequence) == 4

    nodes.removeSelection()
    pt_project.run_close_project()


def test_nodes_error(pt_no_feed):
    nodes = pt_no_feed.layers["nodes"][0]
    node_selection = [74034, 74035]
    nodes.select([f.id() for f in nodes.getFeatures() if f["node_id"] in node_selection])

    dialog = TSPDialog(pt_no_feed)

    dialog.rdo_selected.setChecked(True)
    dialog.rdo_new_layer.setChecked(False)
    dialog.close_window = True
    dialog.cob_minimize.setCurrentText("distance")

    dialog.run()

    msg = "Error:You need at least three nodes to route."
    messagebar = pt_no_feed.iface.messageBar()
    assert messagebar.messages[2][-1] == msg, "Level 2 error message is missing"

    nodes.removeSelection()
    pt_no_feed.run_close_project()


def test_centroid_error(pt_no_feed):
    dialog = TSPDialog(pt_no_feed)

    dialog.rdo_centroids.setChecked(True)
    dialog.rdo_new_layer.setChecked(False)
    dialog.close_window = True
    dialog.cob_minimize.setCurrentText("distance")

    dialog.run()

    msg = "Error:You need at least three centroids to route."
    messagebar = pt_no_feed.iface.messageBar()
    assert messagebar.messages[2][-1] == msg, "Level 2 error message is missing"

    pt_no_feed.run_close_project()


@pytest.mark.parametrize("has_solution", [True, False])
def test_routing_procedure(ae_with_project, has_solution):
    import numpy as np

    if not has_solution:
        project_links = ae_with_project.project.network.links
        project_links.delete(3)
        project_links.delete(4)
        project_links.refresh()

    ae_with_project.project.network.build_graphs()
    graph = ae_with_project.project.network.graphs["c"]
    graph.set_graph("free_flow_time")
    graph.set_skimming(["free_flow_time"])
    graph.set_blocked_centroid_flows(False)

    if not has_solution:
        graph.prepare_graph(np.array([1, 2], dtype=np.int32))

    procedure = TSPProcedure(qgis.utils.iface.mainWindow(), graph, 1, 1)
    procedure.doWork()

    if has_solution:
        assert "Objective function value:" in procedure.report[0]
    else:
        assert procedure.report[0] == "Solution not found"

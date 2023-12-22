import pytest

from qaequilibrae.modules.routing_procedures.tsp_dialog import TSPDialog
from PyQt5.QtCore import Qt
from qgis.core import QgsProject


@pytest.mark.skip("Not implemented")
def test_create_from_centroids(ae_with_project):
    dialog = TSPDialog(ae_with_project)

    dialog.chb_block.setChecked(True)
    dialog.rdo_new_layer.setChecked(False)
    dialog.is_testing = True
    dialog.cob_minimize.setCurrentText("distance")
    
    dialog.run()

    layers = list(QgsProject.instance().mapLayers().values())
    names = [layer.name() for layer in layers]
    
    assert "TSP Solution" in names
    assert "TSP Stops" in names

    QgsProject.instance().clear()

    ae_with_project.run_close_project()

@pytest.mark.skip("Not implemented")
def test_create_from_nodes():
    pass

def test_nodes_error(pt_no_feed):
    nodes = pt_no_feed.layers["nodes"][0]
    node_selection = [74034, 74035]
    nodes.select([f.id() for f in nodes.getFeatures() if f['node_id'] in node_selection])

    dialog = TSPDialog(pt_no_feed)

    dialog.rdo_selected.setChecked(True)
    dialog.rdo_new_layer.setChecked(False)
    dialog.is_testing = True
    dialog.cob_minimize.setCurrentText("distance")

    dialog.run()

    messagebar = pt_no_feed.iface.messageBar()
    assert messagebar.messages[3][0] == ":You need at least three nodes to route. ", "Level 3 error message is missing"

    nodes.removeSelection()
    pt_no_feed.run_close_project()

def test_centroid_error(pt_no_feed):
    dialog = TSPDialog(pt_no_feed)

    dialog.rdo_centroids.setChecked(True)
    dialog.rdo_new_layer.setChecked(False)
    dialog.is_testing = True
    dialog.cob_minimize.setCurrentText("distance")
    
    dialog.run()

    messagebar = pt_no_feed.iface.messageBar()
    assert messagebar.messages[3][1] == ":You need at least three centroids to route. ", "Level 3 error message is missing"

    pt_no_feed.run_close_project()

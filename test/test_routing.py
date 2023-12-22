import pytest

from qaequilibrae.modules.routing_procedures.tsp_dialog import TSPDialog
from PyQt5.QtCore import Qt
from qgis.core import QgsProject


def test_create_from_centroids(ae_with_project):
    dialog = TSPDialog(ae_with_project)

    dialog.chb_block.setChecked(True)
    dialog.rdo_new_layer.setChecked(False)
    dialog.close_window = True
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

def test_centroid_error(pt_project):
    dialog = TSPDialog(pt_project)

    dialog.rdo_new_layer.setChecked(False)
    dialog.close_window = True
    dialog.cob_minimize.setCurrentText("distance")
    
    dialog.run()

    messagebar = pt_project.iface.messageBar()
    assert messagebar.messages[3][0] == ":You need at least three centroids to route. ", "Level 3 error message is missing"

    pt_project.run_close_project()

def test_nodes_error(ae_with_project):
    dialog = TSPDialog(ae_with_project)

    dialog.rdo_selected.setChecked(True)
    dialog.rdo_new_layer.setChecked(False)
    dialog.close_window = True
    dialog.cob_minimize.setCurrentText("distance")
    
    layer = QgsProject.instance().mapLayersByName('nodes')[0]
    layer.removeSelection()
    node_selection = [1,2]
    layer.select([f.id() for f in layer.getFeatures() if f['node_id'] in node_selection])

    dialog.run()

    messagebar = ae_with_project.iface.messageBar()
    assert messagebar.messages[3][0] == ":You need at least three nodes to route. ", "Level 3 error message is missing"


    ae_with_project.run_close_project()
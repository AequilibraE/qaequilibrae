import pytest
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject

from qaequilibrae.modules.paths_procedures.isochrones_dialog import IsochronesDialog


# TODO: ideally, we would test if all the views are correct.
@pytest.mark.parametrize("layer", ["Nodes", "Zones"])
def test_init(ae_with_project, qtbot, timeoutDetector, layer):
    dialog = IsochronesDialog(ae_with_project)

    dialog.cob_minimizing.setCurrentText("distance")
    dialog.cob_skim.setCurrentText("distance")
    dialog.block_paths.setChecked(False)
    dialog.cob_layer.setCurrentText(layer)
    dialog.line_start_id.setText("1")

    qtbot.mouseClick(dialog.but_plot, Qt.LeftButton)

    lyr_name = layer.lower()

    # Check if layer 'skim_viewer' exists
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "skim_viewer" in prj_layers

    # Check if layer 'nodes' or 'zones' is active
    assert lyr_name in prj_layers

    # Check if layer 'nodes' or 'zones' is joined with 'skim_viewer'
    lyr = QgsProject.instance().mapLayersByName(lyr_name)[0]
    field_names = lyr.fields().names()
    assert "skim_viewer_data" in field_names

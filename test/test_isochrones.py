import pytest
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject

from qaequilibrae.modules.matrix_procedures.load_project_data import LoadProjectDataDialog
from qaequilibrae.modules.paths_procedures.isochrones_dialog import IsochronesDialog
from .utilities import run_sfalls_assignment


# TODO: ideally, we would test if all the views are correct.
@pytest.mark.parametrize("layer", ["Nodes", "Zones"])
def test_plot_without_joined_results(ae_with_project, qtbot, timeoutDetector, layer):
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


def test_plot_with_joined_results(ae_with_project, qtbot, timeoutDetector, mocker):
    proj = run_sfalls_assignment(ae_with_project)

    function = "qaequilibrae.modules.matrix_procedures.load_project_data.DisplayAequilibraEFormatsDialog"
    mocker.patch(function)

    dlg = LoadProjectDataDialog(proj, True)

    # Result selection
    dlg.list_results.selectRow(0)
    qtbot.mouseClick(dlg.but_load_Results, Qt.LeftButton)

    # Check if layer 'assignment' exists
    existing_layers = [vector.name() for vector in QgsProject.instance().mapLayers().values()]
    assert "assignment" in existing_layers

    # Check if layer 'links' is set active
    assert "links" in existing_layers

    dialog = IsochronesDialog(ae_with_project)

    # Check if link fields are in the skimmeable fields
    new_fields = [
        "assignment_congested_time",
        "assignment_congested_time_max",
        "assignment_delay_factor",
        "assignment_delay_factor_max",
        "free_flow_time",
        "distance",
    ]
    for field in new_fields:
        assert field in dialog._skimmeable_fields

    dialog.cob_minimizing.setCurrentText("assignment_congested_time")
    dialog.cob_skim.setCurrentText("assignment_congested_time")
    dialog.block_paths.setChecked(False)
    dialog.cob_layer.setCurrentText("Zones")
    dialog.line_start_id.setText("1")

    qtbot.mouseClick(dialog.but_plot, Qt.LeftButton)

    # Check if layer 'skim_viewer' exists
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "skim_viewer" in prj_layers

    # Check if layer 'zones' is active
    assert "zones" in prj_layers

    # Check if layer 'nodes' or 'zones' is joined with 'skim_viewer'
    lyr = QgsProject.instance().mapLayersByName("zones")[0]
    field_names = lyr.fields().names()
    assert "skim_viewer_data" in field_names

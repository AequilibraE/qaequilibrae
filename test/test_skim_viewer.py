import pytest
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject

from qaequilibrae.modules.matrix_procedures.load_project_data import LoadProjectDataDialog
from qaequilibrae.modules.paths_procedures.skim_viewer_dialog import SkimViewerDialog
from .utilities import run_sfalls_assignment


# TODO: ideally, we would test if all the views are correct.
@pytest.mark.parametrize("layer", ["nodes", "zones"])
def test_plot_without_joined_results(ae_with_project, qtbot, timeoutDetector, layer, qgis_iface):
    lyr = ae_with_project.layers[layer][0]
    QgsProject.instance().addMapLayer(lyr)
    qgis_iface.setActiveLayer(lyr)

    dialog = SkimViewerDialog(ae_with_project)

    dialog.cob_minimizing.setCurrentText("distance")
    dialog.cob_skim.setCurrentText("distance")
    dialog.block_paths.setChecked(False)
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


def test_parameter_changed(ae_with_project, qtbot, timeoutDetector, qgis_iface):
    lyr = ae_with_project.layers["nodes"][0]
    QgsProject.instance().addMapLayer(lyr)
    qgis_iface.setActiveLayer(lyr)

    dialog = SkimViewerDialog(ae_with_project)

    dialog.cob_minimizing.setCurrentIndex(8)
    dialog.cob_skim.setCurrentIndex(8)
    dialog.line_start_id.setText("1")

    qtbot.mouseClick(dialog.but_plot, Qt.LeftButton)

    start_skim = dialog.cob_skim.currentText()
    start_cost = dialog.cob_minimizing.currentText()

    # Check if layer 'skim_viewer' exists
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "skim_viewer" in prj_layers

    # Check if layer 'zones' is active
    assert "nodes" in prj_layers

    # Check if layer 'nodes' or 'zones' is joined with 'skim_viewer'
    lyr = QgsProject.instance().mapLayersByName("nodes")[0]
    field_names = lyr.fields().names()
    assert "skim_viewer_data" in field_names

    # Get the values for the 'skim_viewer_data' field
    result1 = [f.attributes()[-1] for f in lyr.getFeatures()]

    # Change the value of block path through centroids
    qtbot.mouseClick(dialog.block_paths, Qt.LeftButton)

    result2 = [f.attributes()[-1] for f in lyr.getFeatures()]

    # Check if the displayed values changed
    assert result1 != result2

    # Change the skimming field
    dialog.cob_skim.setCurrentIndex(4)

    result3 = [f.attributes()[-1] for f in lyr.getFeatures()]

    # Check if the displayed values are the same
    # both free_flow_time and distance fields have the same values, thus it cannot change.
    assert result2 == result3

    # but we can check if the cob_skim variable is not the same
    current_skim = dialog.cob_skim.currentText()
    assert start_skim != current_skim

    # Change the cost field
    dialog.cob_minimizing.setCurrentIndex(4)

    result4 = [f.attributes()[-1] for f in lyr.getFeatures()]
    assert result3 == result4

    current_cost = dialog.cob_minimizing.currentText()
    assert start_cost != current_cost


def test_plot_with_joined_results(ae_with_project, qtbot, timeoutDetector, mocker, qgis_iface):
    lyr = ae_with_project.layers["nodes"][0]
    QgsProject.instance().addMapLayer(lyr)
    qgis_iface.setActiveLayer(lyr)

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

    dialog = SkimViewerDialog(ae_with_project)

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
    dialog.line_start_id.setText("1")

    qtbot.mouseClick(dialog.but_plot, Qt.LeftButton)

    # Check if layer 'skim_viewer' exists
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "skim_viewer" in prj_layers

    # Check if layer 'zones' is active
    assert "nodes" in prj_layers

    # Check if layer 'nodes' or 'zones' is joined with 'skim_viewer'
    lyr = QgsProject.instance().mapLayersByName("nodes")[0]
    field_names = lyr.fields().names()
    assert "skim_viewer_data" in field_names

    # Get the values for the 'skim_viewer_data' field
    result1 = [f.attributes()[-1] for f in lyr.getFeatures()]

    # We select another node to check if the values in the join changed.
    lyr.selectByExpression('"node_id" = 5')

    # Get the values for the 'skim_viewer_data' field
    result2 = [f.attributes()[-1] for f in lyr.getFeatures()]

    # Check if the displayed values changed
    assert result1 != result2


@pytest.mark.parametrize(
    "layer,par,error",
    [
        ("zones", "aaa", "Start ID needs to be a positive integer value"),
        ("zones", "52", "Start ID relates to a non-existing zone"),
        ("nodes", "aaa", "Start ID needs to be a positive integer value"),
        ("nodes", "100", "Start ID relates to a non-existing node"),
    ],
)
def test_start_id_errors(ae_with_project, qtbot, timeoutDetector, layer, par, error, qgis_iface):
    lyr = ae_with_project.layers[layer][0]
    QgsProject.instance().addMapLayer(lyr)
    qgis_iface.setActiveLayer(lyr)

    dialog = SkimViewerDialog(ae_with_project)

    dialog.cob_minimizing.setCurrentText("distance")
    dialog.cob_skim.setCurrentText("distance")
    dialog.block_paths.setChecked(False)
    dialog.line_start_id.setText(par)

    qtbot.mouseClick(dialog.but_plot, Qt.LeftButton)

    messagebar = ae_with_project.iface.messageBar()
    assert messagebar.messages[2][0] == f"Input error:{error}"

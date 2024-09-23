import pytest
from qgis.core import QgsProject

from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog
from qaequilibrae.modules.gis.desire_lines_procedure import DesireLinesProcedure
from qaequilibrae.modules.gis.set_color_ramps_dialog import LoadColorRampSelector
from qaequilibrae.modules.gis.create_bandwidths_dialog import CreateBandwidthsDialog


@pytest.mark.parametrize(
    ("is_delaunay", "a_field", "b_field"), [(True, "matrix_ab", "matrix_ba"), (False, "matrix_AB", "matrix_BA")]
)
def test_bandwidth(ae_with_project, is_delaunay, a_field, b_field):
    # Activate nodes layer
    ae_with_project.load_layer_by_name("nodes")

    line_layer = "DelaunayLines" if is_delaunay else "DesireLines"

    # Create desirelines
    dialog = DesireLinesDialog(ae_with_project)
    dialog.zone_id_field.setCurrentText("node_id")
    dialog.cob_matrices.setCurrentText("demand.aem")
    dialog.set_matrix()
    dialog.matrix.computational_view()
    dialog.radio_delaunay.setChecked(is_delaunay)
    dialog.radio_desire.setChecked(not is_delaunay)
    dialog.worker_thread = DesireLinesProcedure(
        ae_with_project.iface.mainWindow(), "nodes", "node_id", dialog.matrix, dialog.matrix_hash, line_layer
    )

    dialog.worker_thread.doWork()
    dialog.job_finished_from_thread()
    dialog.close()

    # Test if Desireline was indeed created
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert line_layer in prj_layers

    # Create stacked bandwidth
    dialog = CreateBandwidthsDialog(ae_with_project)
    dialog.layer = QgsProject.instance().mapLayersByName(line_layer)[0]
    dialog.ab_FieldComboBox.setCurrentText(a_field)
    dialog.ba_FieldComboBox.setCurrentText(b_field)
    dialog.add_to_bands_list()
    dialog.add_bands_to_map()

    # Test if bandwidth layers were created
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert f"{line_layer} (Color)" in prj_layers
    assert f"{line_layer} (Width)" in prj_layers

    # Clear layers
    QgsProject.instance().clear()


@pytest.mark.parametrize("dual_fields", [True, False])
def test_color_ramp(ae_with_project, dual_fields):
    ae_with_project.load_layer_by_name("nodes")

    # Create desirelines
    dialog = DesireLinesDialog(ae_with_project)
    dialog.zone_id_field.setCurrentText("node_id")
    dialog.cob_matrices.setCurrentText("demand.aem")
    dialog.set_matrix()
    dialog.radio_delaunay.setChecked(True)
    dialog.run()
    dialog.close()

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "DelaunayLines" in prj_layers

    dialog = CreateBandwidthsDialog(ae_with_project)
    dialog.layer = QgsProject.instance().mapLayersByName("DelaunayLines")[0]
    dialog.rdo_ramp.setChecked(True)
    # dialog.ramps = None

    # Create color ramps
    color_ramp = LoadColorRampSelector(dialog.iface, dialog.layer)
    color_ramp.chk_dual_fields.setChecked(dual_fields)
    color_ramp.cbb_ab_color.setCurrentText("Blues")

    color_ramp.set_dual_fields()

    if dual_fields:
        color_ramp.cbb_ab_field.setCurrentText("matrix_tot")
        color_ramp.txt_ab_min.setText("200.0")
        color_ramp.txt_ab_max.setText("46100.0")
        color_ramp.change_field("AB")
    else:
        color_ramp.cbb_ba_color.setCurrentText("Reds")
        color_ramp.cbb_ab_field.setCurrentText("matrix_ab")
        color_ramp.txt_ab_min.setText("100.0")
        color_ramp.txt_ab_max.setText("23000.0")
        color_ramp.cbb_ba_field.setCurrentText("matrix_ba")
        color_ramp.txt_ba_min.setText("100.0")
        color_ramp.txt_ba_max.setText("23100.0")
        color_ramp.change_field("BA")

    color_ramp.load_ramps()

    dialog.ramps = color_ramp.results
    dialog.txt_ramp.setText(str(dialog.ramps))
    dialog.add_to_bands_list()
    dialog.add_bands_to_map()

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "DelaunayLines (Color)" in prj_layers
    assert "DelaunayLines (Width)" in prj_layers

    # Clear layers
    QgsProject.instance().clear()

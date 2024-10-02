import pytest
from qgis.core import QgsProject

from qaequilibrae.modules.gis.set_color_ramps_dialog import LoadColorRampSelector
from qaequilibrae.modules.gis.create_bandwidths_dialog import CreateBandwidthsDialog


line_layer = "lines"


def test_bandwidth(ae, create_links_with_matrix):

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert line_layer in prj_layers

    # Create stacked bandwidth
    dialog = CreateBandwidthsDialog(ae)
    dialog.layer = QgsProject.instance().mapLayersByName(line_layer)[0]
    dialog.ab_FieldComboBox.setCurrentText("matrix_ab")
    dialog.ba_FieldComboBox.setCurrentText("matrix_ba")
    dialog.add_to_bands_list()
    dialog.add_bands_to_map()

    # Test if bandwidth layers were created
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert f"{line_layer} (Color)" in prj_layers
    assert f"{line_layer} (Width)" in prj_layers

    # Clear layers
    QgsProject.instance().clear()


@pytest.mark.parametrize("dual_fields", [True, False])
def test_color_ramp(ae, dual_fields, create_links_with_matrix):

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert line_layer in prj_layers

    dialog = CreateBandwidthsDialog(ae)
    dialog.layer = QgsProject.instance().mapLayersByName(line_layer)[0]
    dialog.rdo_ramp.setChecked(True)
    # dialog.ramps = None

    # Create color ramps
    color_ramp = LoadColorRampSelector(dialog.iface, dialog.layer)
    color_ramp.chk_dual_fields.setChecked(dual_fields)
    color_ramp.cbb_ab_color.setCurrentText("Blues")

    color_ramp.set_dual_fields()

    if dual_fields:
        color_ramp.cbb_ab_field.setCurrentText("matrix_tot")
        color_ramp.txt_ab_min.setText("30")
        color_ramp.txt_ab_max.setText("105")
        color_ramp.change_field("AB")
    else:
        color_ramp.cbb_ba_color.setCurrentText("Reds")
        color_ramp.cbb_ab_field.setCurrentText("matrix_ab")
        color_ramp.txt_ab_min.setText("17")
        color_ramp.txt_ab_max.setText("50")
        color_ramp.cbb_ba_field.setCurrentText("matrix_ba")
        color_ramp.txt_ba_min.setText("11")
        color_ramp.txt_ba_max.setText("63")
        color_ramp.change_field("BA")

    color_ramp.load_ramps()

    dialog.ramps = color_ramp.results
    dialog.txt_ramp.setText(str(dialog.ramps))
    dialog.add_to_bands_list()
    dialog.add_bands_to_map()

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert f"{line_layer} (Color)" in prj_layers
    assert f"{line_layer} (Width)" in prj_layers

    # Clear layers
    QgsProject.instance().clear()

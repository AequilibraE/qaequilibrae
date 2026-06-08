import pytest
import sys
from qgis.core import QgsProject

from qaequilibrae.modules.gis.create_bandwidths_dialog import CreateBandwidthsDialog
from qaequilibrae.modules.gis.set_color_ramps_dialog import LoadColorRampSelector
from .utilities import load_test_layer

link_layer = "link"
pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Running on Windows")


def test_bandwidth(ae, folder_path):
    load_test_layer(folder_path, "link")

    layer = QgsProject.instance().mapLayersByName(link_layer)[0]
    ae.iface.setActiveLayer(layer)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert link_layer in prj_layers

    # Create stacked bandwidth
    dialog = CreateBandwidthsDialog(ae)
    dialog.add_fields_to_cboxes()
    dialog.ab_FieldComboBox.setCurrentIndex(8)
    dialog.ba_FieldComboBox.setCurrentIndex(9)
    dialog.add_to_bands_list()
    dialog.add_bands_to_map()

    # Test if bandwidth layers were created
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert f"{link_layer} (Color)" in prj_layers
    assert f"{link_layer} (Width)" in prj_layers


@pytest.mark.parametrize("dual_fields", [True, False])
def test_color_ramp(ae, folder_path, dual_fields):
    load_test_layer(folder_path, "link")

    layer = QgsProject.instance().mapLayersByName(link_layer)[0]
    ae.iface.setActiveLayer(layer)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert link_layer in prj_layers

    dialog = CreateBandwidthsDialog(ae)
    dialog.add_fields_to_cboxes()
    dialog.rdo_ramp.setChecked(True)

    # Create color ramps
    color_ramp = LoadColorRampSelector(dialog.qgis_project, dialog.layer)
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
    assert f"{link_layer} (Color)" in prj_layers
    assert f"{link_layer} (Width)" in prj_layers

import pytest
from qgis.core import QgsProject

from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog
from qaequilibrae.modules.gis.desire_lines_procedure import DesireLinesProcedure


@pytest.mark.parametrize("is_delaunay", [True, False])
def test_desirelines(ae_with_project, is_delaunay):
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

    layer = QgsProject.instance().mapLayersByName(line_layer)[0]
    target = 62 if is_delaunay else 264
    assert layer.featureCount() == target

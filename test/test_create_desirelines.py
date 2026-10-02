import numpy as np
import pytest
from qgis.core import QgsProject, QgsProcessingContext, QgsProcessingFeedback

from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog
from qaequilibrae.modules.gis.desire_lines_procedure import DesireLinesProcedure
from qaequilibrae.modules.processing_provider.mapping_procedures.delaunay_network import DelaunayNetwork
from qaequilibrae.modules.processing_provider.mapping_procedures.desire_lines import DesireLines


@pytest.mark.parametrize("is_delaunay", [True, False])
@pytest.mark.parametrize("in_memory", [True, False])
def test_desirelines(ae_with_project, is_delaunay, in_memory, mocker):
    # Activate nodes layer
    ae_with_project.load_layer_by_name("nodes")

    line_layer = "DelaunayLines" if is_delaunay else "DesireLines"

    # Create desirelines
    dialog = DesireLinesDialog(ae_with_project)
    dialog.zone_id_field.setCurrentText("node_id")
    dialog.cob_matrices.setCurrentText("demand")
    dialog.set_matrix()
    dialog.matrix.computational_view()
    matrix_path = dialog.matrix.file_path
    if in_memory:
        original = dialog.matrix
        dialog.matrix = original.copy(memory_only=True)
        original.close()
    dialog.radio_delaunay.setChecked(is_delaunay)
    dialog.radio_desire.setChecked(not is_delaunay)
    dialog.worker_thread = DesireLinesProcedure(
        ae_with_project.iface.mainWindow(), "nodes", "node_id", dialog.matrix, line_layer
    )

    algorithm_type = DelaunayNetwork if is_delaunay else DesireLines
    processing = mocker.spy(algorithm_type, "processAlgorithm")
    close = mocker.spy(dialog.matrix, "close")
    dialog.worker_thread.doWork()
    processing.assert_called_once()
    close.assert_not_called()
    dialog.job_finished_from_thread()
    dialog.close()

    # Test if Desireline was indeed created
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert line_layer in prj_layers

    layer = QgsProject.instance().mapLayersByName(line_layer)[0]
    target = 62 if is_delaunay else 264
    assert layer.featureCount() == target

    algorithm = DelaunayNetwork() if is_delaunay else DesireLines()
    algorithm.initAlgorithm()
    context, feedback = QgsProcessingContext(), QgsProcessingFeedback()
    parameters = {
        "NODES" if is_delaunay else "ZONES": QgsProject.instance().mapLayersByName("nodes")[0],
        "NODE_ID_FIELD" if is_delaunay else "ZONE_ID_FIELD": "node_id",
        "MATRIX_PATH": str(matrix_path),
        "MATRIX_CORES": ",".join(dialog.matrix.view_names),
        "BLOCK_CENTROID_FLOWS": False,
        "OUTPUT": "TEMPORARY_OUTPUT",
    }
    result, succeeded = algorithm.run(parameters, context, feedback)
    assert succeeded, feedback.textLog()
    processed = context.takeResultLayer(result["OUTPUT"])

    def flows(output, a_field, b_field):
        suffixes = ("ab", "ba") if is_delaunay else ("AB", "BA")
        directed = {}
        for feature in output.getFeatures():
            a, b = feature[a_field], feature[b_field]
            for core in dialog.matrix.view_names:
                directed[a, b, core] = feature[f"{core}_{suffixes[0]}"]
                directed[b, a, core] = feature[f"{core}_{suffixes[1]}"]
        return directed

    gui_flows = flows(layer, "A_Node", "B_Node")
    processing_flows = flows(processed, "a_node", "b_node")
    assert gui_flows.keys() == processing_flows.keys()
    np.testing.assert_allclose(list(gui_flows.values()), [processing_flows[key] for key in gui_flows], rtol=1e-8)

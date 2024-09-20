import pytest
from qgis.core import QgsProject

from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog
from qaequilibrae.modules.gis.create_bandwidths_dialog import CreateBandwidthsDialog


@pytest.mark.parametrize(
    ("is_delaunay", "a_field", "b_field"), [(True, "matrix_ab", "matrix_ba"), (False, "matrix_AB", "matrix_BA")]
)
def test_bandwidth(ae_with_project, is_delaunay, a_field, b_field):
    # Ativar camada de nós
    ae_with_project.load_layer_by_name("nodes")

    # Criar desirelines
    dialog = DesireLinesDialog(ae_with_project)
    dialog.zone_id_field.setCurrentText("node_id")
    dialog.cob_matrices.setCurrentText("demand.aem")
    dialog.set_matrix()
    dialog.radio_delaunay.setChecked(is_delaunay)
    dialog.radio_desire.setChecked(not is_delaunay)
    dialog.run()
    dialog.close()

    # Testar se o layer foi criado
    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    if is_delaunay:
        assert "DelaunayLines" in prj_layers
    else:
        assert "DesireLines" in prj_layers

    dialog = CreateBandwidthsDialog(ae_with_project)
    dialog.add_fields_to_cboxes()
    dialog.ab_FieldComboBox.setCurrentText(a_field)
    dialog.ba_FieldComboBox.setCurrentText(b_field)
    print(dialog.__dict__)

    # prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]

    # AB flow índice 5 ou "matrix_ab"
    # Add band
    # Create bands

    # Dois novos layers vao ser criados e eles tem que ter um output diferente.
    QgsProject.instance().clear()
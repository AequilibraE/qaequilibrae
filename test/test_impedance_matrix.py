from qgis.PyQt.QtCore import Qt

from qaequilibrae.modules.paths_procedures.impedance_matrix_dialog import ImpedanceMatrixDialog


def test_import_impedance_matrix(ae_with_project, qtbot):
    dialog = ImpedanceMatrixDialog(ae_with_project)

    dialog.block_paths.setChecked(False)
    dialog.line_matrix.setText("imped_matrix_car")
    dialog.available_skims_table.selectRow(4)  # add free_flow_time
    qtbot.mouseClick(dialog.but_adds_to_links, Qt.LeftButton)
    dialog.available_skims_table.selectRow(7)  # add distance
    qtbot.mouseClick(dialog.but_adds_to_links, Qt.LeftButton)

    qtbot.mouseClick(dialog.do_dist_matrix, Qt.LeftButton)

    matrices = dialog.project.matrices
    all_matrices = matrices.list()
    assert "imped_matrix_car" in all_matrices["name"].tolist()

    num_cores = all_matrices[all_matrices["name"] == "imped_matrix_car"]["cores"].values[0]
    assert num_cores == 2

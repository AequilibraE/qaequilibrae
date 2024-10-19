import pytest

from qaequilibrae.modules.paths_procedures.impedance_matrix_dialog import ImpedanceMatrixDialog


def test_import_impedance_matrix(ae_with_project):
    dialog = ImpedanceMatrixDialog(ae_with_project)

    dialog.block_paths.setChecked(False)
    dialog.line_matrix.setText("imped_matrix_car")
    dialog.available_skims_table.selectRow(4)  # add free_flow_time
    dialog.append_to_list()
    dialog.available_skims_table.selectRow(7)  # add distance
    dialog.append_to_list()

    dialog.run_skimming()

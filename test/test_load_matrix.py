import numpy as np
import pandas as pd

from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe
from qaequilibrae.modules.matrix_procedures.load_matrix_dialog import LoadMatrixDialog


# TODO: test removing the matrices
def test_save_matrix(ae_with_project, folder_path, timeoutDetector):
    """A sparse origin/destination/value table becomes a square OMX matrix with a 1-based index."""
    file_name = f"{folder_path}/test_matrix.omx"

    df = pd.read_csv("test/data/SiouxFalls_project/SiouxFalls_od.csv")
    _ = layer_from_dataframe(df, "open_layer")

    dialog = LoadMatrixDialog(ae_with_project)
    dialog.sparse = True
    dialog.output_name = file_name
    dialog.field_from.setCurrentText("O")
    dialog.field_to.setCurrentText("D")
    dialog.field_cells.setCurrentText("Ton")
    dialog.has_errors()
    dialog.worker_thread.signal.connect(dialog.signal_handler)
    dialog.worker_thread.doWork()
    dialog.worker_thread.report = None
    dialog.build_worker_thread()
    dialog.worker_thread.doWork()

    from aequilibrae.matrix import AequilibraeMatrix

    mat = AequilibraeMatrix()
    mat.load(file_name)

    assert mat.get_matrix("ton").shape == (24, 24)
    assert np.sum(np.nan_to_num(mat.get_matrix("ton"))[:, :]) == 360600
    assert (mat.index == np.arange(1, 25)).all()

    dialog.close()

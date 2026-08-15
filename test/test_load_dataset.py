import pandas as pd
import pytest
import qgis
from qgis.core import QgsProject

from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe
from qaequilibrae.modules.matrix_procedures.load_dataset_class import LoadDataset
from qaequilibrae.modules.matrix_procedures.load_dataset_dialog import LoadDatasetDialog


@pytest.mark.parametrize("method", ["csv", "parquet", "open layer"])
def test_load_dialog(ae_with_project, method, folder_path, timeoutDetector):
    df = pd.read_csv("test/data/SiouxFalls_project/synthetic_future_vector.csv")
    _ = layer_from_dataframe(df, "synthetic_future_vector")

    dialog = LoadDatasetDialog(ae_with_project)
    dialog.path = folder_path

    if method in ["csv", "parquet"]:
        dialog.load_fields_to_combo_boxes()
        dialog.cob_data_layer.setCurrentText("synthetic_future_vector")

        out_name = f"{folder_path}/synthetic_future_vector.{method}"
        dialog.load_with_file_name(out_name)

        assert dialog.worker_thread is None

    elif method == "open layer":
        layer = QgsProject.instance().mapLayersByName("synthetic_future_vector")[0]

        dialog.layer = layer
        dialog.radio_layer.setChecked(True)

        dialog.size_it_accordingly(True)
        dialog.cob_index_field.setCurrentText("index")
        dialog.output_name = f"{folder_path}/synthetic_future_vector.csv"
        dialog.cob_data_layer.setCurrentText("synthetic_future_vector")

        dialog.single_use = True
        dialog.load_the_vector()

    assert dialog.selected_fields == ["index", "origins", "destinations"]
    assert dialog.dataset.shape[0] == 24
    assert (dialog.dataset.sum(axis=0)["origins"] == dialog.dataset.sum(axis=0)["destinations"]) > 0


def test_load_dataset_class(folder_path):
    df = pd.read_csv("test/data/SiouxFalls_project/synthetic_future_vector.csv")
    layer = layer_from_dataframe(df, "synthetic_future_vector")

    output_name = f"{folder_path}/synthetic_future_vector.csv"

    action = LoadDataset(
        qgis.utils.iface.mainWindow(),
        layer=layer,
        index_field="index",
        fields=["index", "origins", "destinations"],
        file_name=output_name,
    )

    action.doWork()

    # TODO: add assertions??

import pytest
import numpy as np
import qgis
from PyQt5.QtCore import QVariant
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature

from qaequilibrae.modules.matrix_procedures.load_dataset_dialog import LoadDatasetDialog
from qaequilibrae.modules.matrix_procedures.load_dataset_class import LoadDataset


def load_external_vector():
    import csv

    path_to_csv = "test/data/SiouxFalls_project/synthetic_future_vector.csv"
    datalayer = QgsVectorLayer("None?delimiter=,", "synthetic_future_vector", "memory")

    fields = [
        QgsField("index", QVariant.Int),
        QgsField("origins", QVariant.Double),
        QgsField("destinations", QVariant.Double),
    ]
    datalayer.dataProvider().addAttributes(fields)
    datalayer.updateFields()

    with open(path_to_csv, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            origin = float(row["origins"])
            destination = float(row["destinations"])
            index = int(row["index"])

            feature = QgsFeature()
            feature.setAttributes([index, origin, destination])

            datalayer.dataProvider().addFeature(feature)

    if not datalayer.isValid():
        print("Open layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(datalayer)


# TODO: test with aequilibrae data is creating files in the wrong folder
# @pytest.mark.skip("file modifications")
@pytest.mark.parametrize("method", ["aequilibrae data", "open layer"])
def test_load_dialog(ae_with_project, method, folder_path):
    load_external_vector()
    dialog = LoadDatasetDialog(ae_with_project)
    dialog.path = folder_path

    if method == "aequilibrae data":
        dialog.radio_aequilibrae.setChecked(True)
        dialog.load_fields_to_combo_boxes()
        dialog.cob_data_layer.setCurrentText("synthetic_future_vector")

        out_name = f"{folder_path}/synthetic_future_vector.aed"
        dialog.load_with_file_name(out_name)

        assert dialog.selected_fields == ["index", "origins", "destinations"]
        assert dialog.worker_thread is None
        arr = dialog.dataset.data.tolist()  

    else:
        dialog.radio_layer_matrix.setChecked(True)
        dialog.load_fields_to_combo_boxes()
        dialog.cob_data_layer.setCurrentText("synthetic_future_vector")

        dialog.single_use = True
        dialog.output_name = f"{folder_path}/synthetic_future_vector_TEST.aed"
        dialog.set_output_name()
        dialog.selected_fields.remove("index")
        dialog.worker_thread = LoadDataset(
                    qgis.utils.iface.mainWindow(),
                    layer=dialog.layer,
                    index_field="index",
                    fields=dialog.selected_fields,
                    file_name=dialog.output_name,
                )
        dialog.worker_thread.doWork()

        assert dialog.selected_fields == ["origins", "destinations"]
        assert dialog.dataset is None
        arr = dialog.worker_thread.output.data.tolist()

    assert len(arr) == 24
    assert np.sum(arr, axis=0)[1] == np.sum(arr, axis=0)[2] > 0

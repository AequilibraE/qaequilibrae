import pytest
import numpy as np
from PyQt5.QtCore import QVariant
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature

from qaequilibrae.modules.matrix_procedures.load_dataset_dialog import LoadDatasetDialog


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

@pytest.mark.parametrize("method", ["aequilibrae data", "open layer"])
def test_load_dialog(ae_with_project, method):
    load_external_vector()
    dialog = LoadDatasetDialog(ae_with_project)
    dialog._testing = True

    if method == "aequilibrae data":
        dialog.radio_aequilibrae.setChecked(True)
        dialog.load_fields_to_combo_boxes()
        dialog.cob_data_layer.setCurrentText("synthetic_future_vector")

        dialog.out_name = "test/data/SiouxFalls_project/synthetic_future_vector.aed"
        dialog.load_from_aequilibrae_format()

        assert dialog.selected_fields == ["index", "origins", "destinations"]
        assert dialog.worker_thread is None
        arr = dialog.dataset.data.tolist()

    else:
        dialog.radio_layer_matrix.setChecked(True)
        dialog.load_fields_to_combo_boxes()
        dialog.cob_data_layer.setCurrentText("synthetic_future_vector")

        dialog.load_the_vector()
        dialog.worker_thread.doWork()
        dialog.output_name = "test/data/SiouxFalls_project/synthetic_future_vector_TEST.aed"

        assert dialog.selected_fields == ["origins", "destinations"]
        assert dialog.dataset is None
        arr = dialog.worker_thread.output.data.tolist()

    assert len(arr) == 24
    assert np.sum(arr, axis=0)[1] == np.sum(arr, axis=0)[2] > 0
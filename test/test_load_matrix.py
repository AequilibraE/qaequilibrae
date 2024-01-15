from unittest import mock
from PyQt5.QtCore import Qt, QTimer, QVariant
import numpy as np
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsApplication
from qaequilibrae.modules.matrix_procedures.load_matrix_dialog import LoadMatrixDialog


def load_layers():
    import csv

    path_to_csv = "test/data/SiouxFalls_project/SiouxFalls_od.csv"
    datalayer = QgsVectorLayer("None?delimiter=,", "open_layer", "memory")

    fields = [
        QgsField("O", QVariant.Int),
        QgsField("D", QVariant.Int),
        QgsField("Ton", QVariant.Double),
    ]
    datalayer.dataProvider().addAttributes(fields)
    datalayer.updateFields()

    with open(path_to_csv, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            origin = int(row["O"])
            destination = int(row["D"])
            tons = float(row["Ton"])

            feature = QgsFeature()
            feature.setAttributes([origin, destination, tons])

            datalayer.dataProvider().addFeature(feature)

    if not datalayer.isValid():
        print("Open layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(datalayer)


def test_matrix_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.matrix_procedures.load_matrix_dialog import LoadMatrixDialog
    from test.test_qaequilibrae_menu_with_project import check_if_new_active_window_matches_class

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LoadMatrixDialog)

    action = ae_with_project.menuActions["Data"][1]
    assert action.text() == "Import matrices", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()

# TODO: test removing the matrices
def test_save_matrix(ae_with_project):
    file_name = "test/data/SiouxFalls_project/matrices/test_matrix.aem"
    load_layers()
    dialog = LoadMatrixDialog(ae_with_project)
    dialog._testing = True
    dialog.sparse = True
    dialog.output_name = file_name
    dialog.field_from.setCurrentText("O")
    dialog.field_to.setCurrentText("D")
    dialog.field_cells.setCurrentText("Ton")
    dialog.load_the_matrix()
    dialog.worker_thread.doWork()
    dialog.finished_threaded_procedure("LOADED-MATRIX")
    dialog.prepare_final_matrix()
    dialog.worker_thread.doWork()

    from aequilibrae.matrix import AequilibraeMatrix

    mat = AequilibraeMatrix()
    mat.load(file_name)

    assert mat.matrix["ton"].shape == (24, 24)
    assert np.sum(np.nan_to_num(mat.matrix["ton"])[:, :]) == 360600
    assert (mat.index == np.arange(1, 25)).all()

    dialog.close()

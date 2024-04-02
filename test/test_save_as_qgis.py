import pytest
from os.path import join, isfile
from uuid import uuid4

from PyQt5.QtCore import QVariant
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qaequilibrae.modules.menu_actions.save_as_qgis import SaveAsQGZ

@pytest.fixture
def folder_path(tmp_path):
    return join(tmp_path, uuid4().hex)


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

# TODO: This test is incomplete. Missing other databases and assertion of qgz file not empty
def test_save_as_qgis(ae_with_project, folder_path, mocker):

    load_layers()

    file_path = f"{folder_path}/text.qgz"
    function = "qaequilibrae.modules.menu_actions.save_as_qgis.SaveAsQGZ.choose_output"
    mocker.patch(function, return_value=file_path)

    dialog = SaveAsQGZ(ae_with_project)
    print(dialog.output_path.text())
    dialog.run()

    assert isfile(join(dialog.qgis_project.project.project_base_path, "qgis_layers.sqlite"))

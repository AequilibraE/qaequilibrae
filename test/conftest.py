import pytest
from os.path import join
from uuid import uuid4
from shutil import copytree
from PyQt5.QtCore import QTimer, QVariant
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qgis.core import QgsPointXY, QgsGeometry
from qgis.PyQt.QtCore import QVariant
from qaequilibrae.qaequilibrae import AequilibraEMenu
from qaequilibrae.modules.common_tools import ReportDialog


@pytest.fixture
def folder_path(tmp_path):
    return join(tmp_path, uuid4().hex)


@pytest.fixture(scope="function")
def ae(qgis_iface) -> AequilibraEMenu:
    return AequilibraEMenu(qgis_iface)


@pytest.fixture(scope="function")
def ae_with_project(qgis_iface, folder_path) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    copytree("test/data/SiouxFalls_project", folder_path)
    _run_load_project_from_path(ae, folder_path)
    yield ae
    ae.run_close_project()


@pytest.fixture(scope="function")
def timeoutDetector(qgis_iface) -> None:
    def handle_trigger():
        # Check if a report window has openned
        window = QApplication.activeWindow()
        if isinstance(window, ReportDialog):
            window.close()
            raise Exception("Test timed out because of a report dialog showing")
        else:
            if window:
                window.close()
            raise Exception("Test timed out")

    timer = QTimer()
    timer.timeout.connect(handle_trigger)
    timer.setSingleShot(True)
    timer.start(3000)
    yield timer
    timer.stop()


@pytest.fixture(scope="function")
def pt_project(qgis_iface, folder_path) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    copytree("test/data/coquimbo_project", folder_path)
    _run_load_project_from_path(ae, folder_path)
    yield ae
    ae.run_close_project()


@pytest.fixture(scope="function")
def pt_no_feed(qgis_iface, folder_path) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    copytree("test/data/no_pt_feed", folder_path)
    _run_load_project_from_path(ae, folder_path)
    yield ae
    ae.run_close_project()


@pytest.fixture(scope="function")
def load_layers_from_csv():
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


@pytest.fixture
def create_example(folder_path):
    from aequilibrae.utils.create_example import create_example

    project = create_example(folder_path, "coquimbo")
    project.close()
    yield folder_path


@pytest.fixture
def coquimbo_project(qgis_iface, create_example) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    _run_load_project_from_path(ae, create_example)
    yield ae
    ae.run_close_project()


@pytest.fixture
def create_links_with_matrix():
    layer = QgsVectorLayer("Linestring?crs=epsg:4326", "lines", "memory")
    if not layer.isValid():
        print("lines layer failed to load!")
    else:
        field_id = QgsField("link_id", QVariant.Int)
        matrix_ab = QgsField("matrix_ab", QVariant.Int)
        matrix_ba = QgsField("matrix_ba", QVariant.Int)
        matrix_tot = QgsField("matrix_tot", QVariant.Int)

        layer.dataProvider().addAttributes([field_id, matrix_ab, matrix_ba, matrix_tot])
        layer.updateFields()

        lines = [
            [QgsPointXY(1, 0), QgsPointXY(1, 1)],
            [QgsPointXY(1, 0), QgsPointXY(0, 0)],
            [QgsPointXY(0, 0), QgsPointXY(0, 1)],
            [QgsPointXY(0, 1), QgsPointXY(1, 1)],
            [QgsPointXY(0, 0), QgsPointXY(1, 1)],
        ]

        attributes = ([1, 2, 3, 4, 5], [50, 42, 17, 32, 19], [50, 63, 18, 32, 11], [100, 105, 35, 64, 30])

        features = []
        for i, (line, fid, ab, ba, tot) in enumerate(zip(lines, *attributes)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolylineXY(line))
            feature.setAttributes([fid, ab, ba, tot])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(layer)

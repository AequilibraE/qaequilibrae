import pytest
from PyQt5.QtCore import QTimer, QVariant
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qaequilibrae.qaequilibrae import AequilibraEMenu
from qaequilibrae.modules.common_tools import ReportDialog


@pytest.fixture(scope="function")
def ae(qgis_iface) -> AequilibraEMenu:
    return AequilibraEMenu(qgis_iface)


@pytest.fixture(scope="function")
def ae_with_project(qgis_iface) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    _run_load_project_from_path(ae, "test/data/SiouxFalls_project")
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
def pt_project(qgis_iface) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    _run_load_project_from_path(ae, "test/data/coquimbo_project")
    yield ae
    ae.run_close_project()


@pytest.fixture(scope="function")
def pt_no_feed(qgis_iface) -> AequilibraEMenu:
    ae = AequilibraEMenu(qgis_iface)
    from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

    _run_load_project_from_path(ae, "test/data/no_pt_feed")
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

import pytest
from os.path import join
from uuid import uuid4
from shutil import copytree
from PyQt5.QtCore import QTimer, QVariant
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature
from qgis.core import QgsPointXY, QgsGeometry, QgsCoordinateReferenceSystem
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


@pytest.fixture
def run_assignment(ae_with_project):
    from aequilibrae.paths import TrafficAssignment, TrafficClass

    project = ae_with_project.project
    project.network.build_graphs()

    graph = project.network.graphs["c"]
    graph.set_graph("free_flow_time")
    graph.set_skimming(["free_flow_time", "distance"])
    graph.set_blocked_centroid_flows(False)

    demand = project.matrices.get_matrix("demand.aem")
    demand.computational_view(["matrix"])

    assigclass = TrafficClass("car", graph, demand)

    assig = TrafficAssignment()

    assig.set_classes([assigclass])
    assig.set_vdf("BPR")
    assig.set_vdf_parameters({"alpha": "b", "beta": "power"})
    assig.set_capacity_field("capacity")
    assig.set_time_field("free_flow_time")
    assig.set_algorithm("bfw")
    assig.max_iter = 5
    assig.rgap_target = 0.01
    assig.execute()

    assig.save_results("assignment")
    assig.save_skims("assignment", which_ones="all", format="omx")

    return ae_with_project


@pytest.fixture
def create_polygons_layer(request):
    layer = QgsVectorLayer("Polygon?crs=epsg:4326", "polygon", "memory")
    if not layer.isValid():
        print("Polygon layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        field_zone_id = QgsField("zone_id", QVariant.Int)
        nickname = QgsField("name", QVariant.String)

        layer.dataProvider().addAttributes([field_id, field_zone_id, nickname])
        layer.updateFields()

        polys = [
            [
                QgsPointXY(-71.2487, -29.8936),
                QgsPointXY(-71.2487, -29.8895),
                QgsPointXY(-71.2441, -29.8895),
                QgsPointXY(-71.2441, -29.8936),
                QgsPointXY(-71.2487, -29.8936),
            ],
            [
                QgsPointXY(-71.2401, -29.8945),
                QgsPointXY(-71.2401, -29.8928),
                QgsPointXY(-71.2375, -29.8928),
                QgsPointXY(-71.2375, -29.8945),
                QgsPointXY(-71.2401, -29.8945),
            ],
            [
                QgsPointXY(-71.2329, -29.8800),
                QgsPointXY(-71.2329, -29.8758),
                QgsPointXY(-71.2280, -29.8758),
                QgsPointXY(-71.2280, -29.8800),
                QgsPointXY(-71.2329, -29.8800),
            ],
        ]

        attributes = (request.param, [None, None, None])

        features = []
        for i, (poly, zone_id, name) in enumerate(zip(polys, *attributes)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolygonXY([poly]))
            feature.setAttributes([i + 1, zone_id, name])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(layer)

    return layer


@pytest.fixture
def load_sfalls_from_layer(folder_path, request):

    p = "test/data/SiouxFalls_project" if request.param == None else folder_path
    path_to_gpkg = f"{p}/SiouxFalls.gpkg"

    # append the layername part
    gpkg_links_layer = path_to_gpkg + "|layername=links"
    gpkg_nodes_layer = path_to_gpkg + "|layername=nodes"

    linkslayer = QgsVectorLayer(gpkg_links_layer, "Links layer", "ogr")
    nodeslayer = QgsVectorLayer(gpkg_nodes_layer, "Nodes layer", "ogr")

    if not linkslayer.isValid():
        print("Links layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(linkslayer)

    if not nodeslayer.isValid():
        print("Nodes layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(nodeslayer)
        var = QgsProject.instance().mapLayersByName("Nodes layer")
        if not var[0].crs().isValid():
            crs = QgsCoordinateReferenceSystem("EPSG:4326")
            var[0].setCrs(crs)


@pytest.fixture
def load_synthetic_future_vector():
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

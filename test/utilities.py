# coding=utf-8
"""Common functionality used by regression tests."""

import logging
import os
import sys
from os.path import abspath, dirname, exists, join
from shutil import copyfile

import numpy as np
from PyQt5.QtCore import QVariant
from aequilibrae.matrix import AequilibraeMatrix
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)

LOGGER = logging.getLogger("QGIS")
QGIS_APP = None  # Static variable used to hold hand to running QGIS app
CANVAS = None
PARENT = None
IFACE = None


def get_qgis_app():
    """Start one QGIS application to test against.

    :returns: Handle to QGIS app, canvas, iface and parent. If there are any
        errors the tuple members will be returned as None.
    :rtype: (QgsApplication, CANVAS, IFACE, PARENT)

    If QGIS is already running the handle to that app will be returned.
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, abspath(join(dirname(dirname(__file__)), "qaequilibrae")))
    try:
        from qgis.PyQt import QtGui, QtCore
        from qgis.core import QgsApplication
        from qgis.gui import QgsMapCanvas
        from .qgis_interface import QgisInterface
    except ImportError:
        return None, None, None, None

    global QGIS_APP  # pylint: disable=W0603

    if QGIS_APP is None:
        gui_flag = True  # All test will run qgis in gui mode
        # noinspection PyPep8Naming
        QGIS_APP = QgsApplication(sys.argv, gui_flag)
        # Make sure QGIS_PREFIX_PATH is set in your env if needed!
        QGIS_APP.initQgis()
        s = QGIS_APP.showSettings()
        LOGGER.debug(s)

    global PARENT  # pylint: disable=W0603
    if PARENT is None:
        # noinspection PyPep8Naming
        PARENT = QtGui.QWidget()

    global CANVAS  # pylint: disable=W0603
    if CANVAS is None:
        # noinspection PyPep8Naming
        CANVAS = QgsMapCanvas(PARENT)
        CANVAS.resize(QtCore.QSize(400, 400))

    global IFACE  # pylint: disable=W0603
    if IFACE is None:
        # QgisInterface is a stub implementation of the QGIS plugin interface
        # noinspection PyPep8Naming
        IFACE = QgisInterface(CANVAS)

    return QGIS_APP, CANVAS, IFACE, PARENT


def create_centroids_layer():
    """Creates a vector layer in memory named 'Centroids' to be used with Coquimbo data."""

    nodes_layer = QgsVectorLayer("Point?crs=epsg:4326", "Centroids", "memory")
    if not nodes_layer.isValid():
        print("Nodes layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        nodes_layer.dataProvider().addAttributes([field_id])

        field_zone_id = QgsField("zone_id", QVariant.Int)
        nodes_layer.dataProvider().addAttributes([field_zone_id])

        nodes_layer.updateFields()
        points = [
            QgsPointXY(-71.3509, -29.9393),
            QgsPointXY(-71.3182, -29.9619),
            QgsPointXY(12.4606, 41.9093),
        ]

        zone_ids = [97, 98, 99]

        features = []
        for i, (point, zone_id) in enumerate(zip(points, zone_ids)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(point))
            feature.setAttributes([i + 1, zone_id])
            features.append(feature)

        nodes_layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(nodes_layer)


def create_nodes_layer(index):
    """Creates a point layer in memory to be used with Coquimbo data."""
    layer = QgsVectorLayer("Point?crs=epsg:4326", "point", "memory")
    if not layer.isValid():
        print("Nodes layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        field_zone_id = QgsField("zone_id", QVariant.Int)
        nickname = QgsField("name", QVariant.String)

        layer.dataProvider().addAttributes([field_id, field_zone_id, nickname])
        layer.updateFields()

        points = [
            QgsPointXY(-71.2489, -29.8936),
            QgsPointXY(-71.2355, -29.8947),
            QgsPointXY(-71.2350, -29.8875),
        ]

        attributes = (index, [None, None, None])

        features = []
        for i, (point, zone_id, name) in enumerate(zip(points, *attributes)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(point))
            feature.setAttributes([i + 1, zone_id, name])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(layer)

    return layer


def create_links_layer(index):
    """Creates a line layer in memory to be used with Coquimbo data."""
    layer = QgsVectorLayer("Linestring?crs=epsg:4326", "linestring", "memory")
    if not layer.isValid():
        print("linestring layer failed to load!")
    else:
        field_id = QgsField("ID", QVariant.Int)
        field_zone_id = QgsField("zone_id", QVariant.Int)
        nickname = QgsField("name", QVariant.String)

        layer.dataProvider().addAttributes([field_id, field_zone_id, nickname])
        layer.updateFields()

        lines = [
            [QgsPointXY(-71.2517, -29.8880), QgsPointXY(-71.2498, -29.8944)],
            [QgsPointXY(-71.2389, -29.8943), QgsPointXY(-71.2342, -29.8933)],
            [QgsPointXY(-71.2397, -29.8836), QgsPointXY(-71.2341, -29.8805)],
        ]

        attributes = (index, [None, None, None])

        features = []
        for i, (line, zone_id, name) in enumerate(zip(lines, *attributes)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolylineXY(line))
            feature.setAttributes([i + 1, zone_id, name])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(layer)

    return layer


def create_polygons_layer(index):
    """Creates a polygon layer in memory to be used with Coquimbo data."""
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

        attributes = (index, [None, None, None])

        features = []
        for i, (poly, zone_id, name) in enumerate(zip(polys, *attributes)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolygonXY([poly]))
            feature.setAttributes([i + 1, zone_id, name])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        QgsProject.instance().addMapLayer(layer)

        return layer


def load_sfalls_from_layer(path):
    """Creates Sioux Falls links and nodes layers"""

    path_to_gpkg = f"{path}/SiouxFalls.gpkg"

    if not exists(path):
        os.makedirs(path)
    copyfile("test/data/SiouxFalls_project/SiouxFalls.gpkg", path_to_gpkg)

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


def run_sfalls_assignment(aeq_from_qgis):
    """Runs traffic assignment with Sioux Falls data."""

    from aequilibrae.paths import TrafficAssignment, TrafficClass

    project = aeq_from_qgis.project
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

    return aeq_from_qgis


def load_test_layer(folder, file_name):
    """Loads generic links and nodes layers."""

    if not exists(folder):
        os.makedirs(folder)
    copyfile(f"test/data/NetworkPreparation/{file_name}.csv", f"{folder}/{file_name}.csv")

    csv_path = f"{folder}/{file_name}.csv"

    if file_name == "link":
        uri = "file://{}?delimiter=,&crs=epsg:4326&wktField={}".format(csv_path, "geometry")
    else:
        uri = "file://{}?delimiter=,&crs=epsg:4326&xField={}&yField={}".format(csv_path, "x", "y")

    layer = QgsVectorLayer(uri, file_name, "delimitedtext")

    if not layer.isValid():
        print("Layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(layer)


def create_matrix(index: np.ndarray, path: str):
    """Creates a square-matrix in which all the elements are the number 10."""

    names_list = ["demand"]
    zones = index.shape[0]

    mat = AequilibraeMatrix()
    mat.create_empty(zones=zones, matrix_names=names_list, memory_only=False, file_name=path)
    mat.index[:] = index[:]

    for name in names_list:
        mat.matrix[name][:, :] = np.full((zones, zones), 10.0)[:, :]

    mat.matrices.flush()

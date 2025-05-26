import re
import shutil
import sqlite3
import sys
from os import environ, makedirs
from os.path import isfile, join

import numpy as np
import openmatrix as omx
import pandas as pd
import pytest
from PyQt5.QtCore import QMetaType
from aequilibrae import Project
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.transit import Transit
from aequilibrae.utils.create_example import create_example
from qgis.core import (
    QgsApplication,
    QgsField,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
)
from shapely.geometry import Point

from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe
from qaequilibrae.modules.processing_provider.Add_connectors import AddConnectors
from qaequilibrae.modules.processing_provider.add_links_from_layer import AddLinksFromLayer
from qaequilibrae.modules.processing_provider.add_matrix_from_layer import AddMatrixFromLayer
from qaequilibrae.modules.processing_provider.assign_traffic_from_yaml import TrafficAssignYAML
from qaequilibrae.modules.processing_provider.assign_transit_from_yaml import TransitAssignYAML
from qaequilibrae.modules.processing_provider.collapse_links import CollapseLinks
from qaequilibrae.modules.processing_provider.create_matrix_from_layer import CreateMatrixFromLayer
from qaequilibrae.modules.processing_provider.create_transit_graph import CreatePTGraph
from qaequilibrae.modules.processing_provider.export_matrix import ExportMatrix
from qaequilibrae.modules.processing_provider.import_gtfs import ImportGTFS
from qaequilibrae.modules.processing_provider.matrix_calculator import MatrixCalculator
from qaequilibrae.modules.processing_provider.network_simplifier import NetworkSimplifier
from qaequilibrae.modules.processing_provider.project_from_OSM import ProjectFromOSM
from qaequilibrae.modules.processing_provider.project_from_layer import ProjectFromLayer
from qaequilibrae.modules.processing_provider.provider import Provider
from qaequilibrae.modules.processing_provider.renumber_nodes_from_layer import RenumberNodesFromLayer
from qaequilibrae.modules.processing_provider.trip_length_distribution import TripLengthDistribution
from .utilities import load_sfalls_from_layer, load_test_layer

pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Running on Windows")


def qgis_app():
    qgs = QgsApplication([], False)
    qgs.initQgis()
    yield qgs
    qgs.exitQgis()


def test_provider_exists(qgis_app):
    provider = Provider()
    QgsApplication.processingRegistry().addProvider(provider)

    registry = QgsApplication.processingRegistry()
    provider_names = [p.name().lower() for p in registry.providers()]
    assert "aequilibrae" in provider_names


@pytest.mark.parametrize("format", [0, 1, 2])
@pytest.mark.parametrize("source_file", ["sfalls_skims.omx", "demand.aem"])
def test_export_matrix(folder_path, source_file, format):
    makedirs(folder_path)

    parameters = {
        "matrix_path": f"test/data/SiouxFalls_project/matrices/{source_file}",
        "file_path": folder_path,
        "output_format": format,
    }

    action = ExportMatrix()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    assert isfile(result["Output"])


def test_matrix_from_layer(folder_path):
    makedirs(folder_path)

    df = pd.read_csv("test/data/SiouxFalls_project/SiouxFalls_od.csv")
    layer = layer_from_dataframe(df, "SiouxFalls_od")

    parameters = {
        "matrix_layer": layer,
        "origin": "O",
        "destination": "D",
        "value": "Ton",
        "file_path": join(folder_path, "demand.omx"),
        "matrix_core": "MAT_CORE",
    }

    action = AddMatrixFromLayer()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    _ = action.run(parameters, context, feedback)

    assert isfile(parameters["file_path"])

    mat = omx.open_file(parameters["file_path"])
    assert "MAT_CORE" in mat.list_matrices()

    m = np.array(mat["MAT_CORE"])
    assert m.shape == (24, 24)
    assert m.sum() == 360600


def test_project_from_layer(folder_path):
    load_sfalls_from_layer(folder_path)

    linkslayer = QgsProject.instance().mapLayersByName("Links layer")[0]

    linkslayer.startEditing()
    field = QgsField("ltype", QMetaType.Type.QString)
    linkslayer.addAttribute(field)
    linkslayer.updateFields()

    for feature in linkslayer.getFeatures():
        feature["ltype"] = "road"
        linkslayer.updateFeature(feature)

    linkslayer.commitChanges()

    parameters = {
        "links": linkslayer,
        "link_id": "link_id",
        "link_type": "ltype",
        "direction": "direction",
        "modes": "modes",
        "project_path": f"{folder_path}/new_project",
    }

    action = ProjectFromLayer()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.run(parameters, context, feedback)
    assert result[0]["Output"] == parameters["project_path"]

    project = Project()
    project.open(parameters["project_path"])

    assert project.network.count_links() == 76
    assert project.network.count_nodes() == 24


def test_add_centroid_connector(pt_no_feed):
    project = pt_no_feed.project
    project_folder = project.project_base_path

    nodes = project.network.nodes

    cnt = nodes.new_centroid(100_000)
    cnt.geometry = Point(-71.34, -29.95)
    cnt.save()

    parameters = {"num_connectors": 3, "mode": "c", "project_path": project_folder}

    action = AddConnectors()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    assert result["Output"] == project_folder

    with project.db_connection as conn:
        node_qry = "select count(node_id) from nodes where is_centroid=1"
        node_count = conn.execute(node_qry).fetchone()[0]
        assert node_count == 1

        link_qry = "select count(name) from links where name like 'centroid connector%'"
        link_count = conn.execute(link_qry).fetchone()[0]
        assert link_count == 3


def test_renumber_from_centroids(ae_with_project, tmp_path):
    load_sfalls_from_layer(tmp_path)

    project = ae_with_project.project
    project_folder = project.project_base_path

    nodeslayer = QgsProject.instance().mapLayersByName("Nodes layer")[0]

    nodeslayer.startEditing()
    for feat in nodeslayer.getFeatures():
        value = feat["id"] + 1000
        nodeslayer.changeAttributeValue(feat.id(), nodeslayer.fields().indexFromName("id"), value)

    nodeslayer.commitChanges()

    parameters = {"nodes": nodeslayer, "node_id": "id", "project_path": project_folder}

    action = RenumberNodesFromLayer()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.run(parameters, context, feedback)

    assert result[0]["Output"] == project_folder

    with project.db_connection as conn:
        node_qry = "select node_id from nodes;"
        node_count = conn.execute(node_qry).fetchall()
        node_count = [n[0] for n in node_count]
        assert node_count == list(range(1001, 1025))


def test_assign_from_yaml(ae_with_project):
    folder = str(ae_with_project.project.project_base_path)
    file_path = join(folder, "config.yml")

    assert isfile(file_path)

    string_to_replace = "path_to_project"

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    updated_content = re.sub(re.escape(string_to_replace), folder, content)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(updated_content)

    parameters = {"conf_file": file_path}

    action = TrafficAssignYAML()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    assert result["Output"] == "Traffic assignment successfully completed"

    assert isfile(join(folder, "results_database.sqlite"))

    conn = sqlite3.connect(join(folder, "results_database.sqlite"))
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()[0]
    assert tables == "test_from_yaml"

    row = conn.execute("SELECT * FROM test_from_yaml;").fetchone()
    assert row


def test_create_pt_graph(coquimbo_project):

    project = coquimbo_project.project
    project_folder = project.project_base_path

    parameters = {
        "project_path": project_folder,
        "access_mode": "c",
        "block_flows": False,
        "walking_edges": False,
        "outer_stops_transfers": False,
    }

    action = CreatePTGraph()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.run(parameters, context, feedback)
    assert result[0]["Output"] == "PT graph successfully created"

    periods = project.network.periods
    assert periods.data.shape[0] == 1


@pytest.mark.parametrize("allow_map_match", [True, False])
def test_import_gtfs(pt_no_feed, allow_map_match):
    project = pt_no_feed.project
    project_folder = project.project_base_path

    parameters = {
        "project_path": project_folder,
        "gtfs_file": "test/data/coquimbo_project/gtfs_coquimbo.zip",
        "gtfs_agency": "Lisanco",
        "gtfs_date": "2016-04-16",
        "allow_map_match": allow_map_match,
    }

    action = ImportGTFS()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.run(parameters, context, feedback)
    assert result[0]["Output"] == "Traffic assignment successfully completed"


def test_add_links_from_layer(ae_with_project):
    folder_path = ae_with_project.project.project_base_path

    load_test_layer(ae_with_project.project.project_base_path, "link")
    layer = QgsProject.instance().mapLayersByName("link")[0]

    parameters = {
        "links": layer,
        "link_type": "link_type",
        "direction": "direction",
        "modes": "modes",
        "project_path": ae_with_project.project.project_base_path,
    }

    action = AddLinksFromLayer()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    _ = action.run(parameters, context, feedback)

    project = Project()
    project.open(folder_path)

    assert project.network.count_links() == 81
    assert project.network.count_nodes() == 28


def test_assign_transit_from_yaml(coquimbo_project):
    folder = str(coquimbo_project.project.project_base_path)
    shutil.copyfile("test/data/coquimbo_project/transit_config.yml", f"{folder}/transit_config.yml")
    shutil.copyfile("test/data/coquimbo_project/matrices/demand.aem", f"{folder}/matrices/demand.aem")

    file_path = join(folder, "transit_config.yml")
    assert isfile(file_path)

    string_to_replace = "path_to_project"

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    updated_content = re.sub(re.escape(string_to_replace), folder, content)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(updated_content)

    data = Transit(coquimbo_project.project)
    graph = data.create_graph(
        with_outer_stop_transfers=False,
        with_walking_edges=False,
        blocking_centroid_flows=False,
        connector_method="overlapping_regions",
    )

    coquimbo_project.project.network.build_graphs()
    graph.create_line_geometry(method="connector project match", graph="c")

    data.save_graphs()

    parameters = {"conf_file": file_path}

    action = TransitAssignYAML()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    assert result["Output"] == "Transit assignment successfully completed"

    assert isfile(join(folder, "results_database.sqlite"))

    conn = sqlite3.connect(join(folder, "results_database.sqlite"))
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()[0]
    assert tables == "transit_from_yaml"

    row = conn.execute("SELECT * FROM transit_from_yaml;").fetchone()
    assert row


def test_create_matrix_from_layer(folder_path):
    makedirs(folder_path)

    df = pd.read_csv("test/data/SiouxFalls_project/SiouxFalls_od.csv")
    layer = layer_from_dataframe(df, "SiouxFalls_od")

    parameters = {
        "matrix_layer": layer,
        "origin": "O",
        "destination": "D",
        "value": "Ton",
        "file_path": join(folder_path, "siouxfalls_od.aem"),
        "matrix_core": "MAT_CORE",
    }

    action = CreateMatrixFromLayer()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    _ = action.run(parameters, context, feedback)
    assert isfile(parameters["file_path"])

    mat = AequilibraeMatrix()
    mat.load(parameters["file_path"])

    info = mat.__dict__
    assert info["names"] == [parameters["matrix_core"]]
    assert info["zones"] == 24
    assert np.sum(info["matrix"][parameters["matrix_core"]][:, :]) == 360600


def test_matrix_calc(folder_path):
    makedirs(folder_path)

    parameters = {
        "conf_file": "test/data/SiouxFalls_project/matrix_config.yml",
        "procedure": "(cars - (heavy_vehicles * 0.25)).T",
        "file_path": f"{folder_path}/hello.aem",
        "matrix_core": "new_core",
    }

    action = MatrixCalculator()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    _ = action.run(parameters, context, feedback)

    assert isfile(parameters["file_path"])
    mat = AequilibraeMatrix()
    mat.load(parameters["file_path"])

    info = mat.__dict__
    assert info["names"] == [parameters["matrix_core"]]
    assert info["zones"] == 24
    assert np.sum(info["matrix"][parameters["matrix_core"]][:, :]) > 0


@pytest.mark.skipif(not bool(environ.get("CI")), reason="Runs only in GitHub Action")
def test_project_from_osm(folder_path):

    parameters = {"place_name": "Abrolhos", "project_path": folder_path}

    action = ProjectFromOSM()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    _ = action.run(parameters, context, feedback)

    project = Project()
    project.open(folder_path)

    assert project.network.count_links() == 11
    assert project.network.count_nodes() == 10


def test_trip_length_distribution(ae_with_project, folder_path):
    matrices = ae_with_project.project.matrices
    mat_names = matrices.list()["name"].tolist()

    parameters = {
        "demand_mat_name": 3,
        "demand_mat_core": "matrix",
        "skim_mat_name": 5,
        "skim_mat_core": "distance_blended",
        "file_path": join(folder_path, "my_file.png"),
    }

    action = TripLengthDistribution()
    action.matrices = matrices
    action.mat_names = mat_names

    # Mock context and feedback
    class DummyContext:
        pass

    class DummyFeedback:
        def pushInfo(self, msg):
            pass

        def reportError(self, msg):
            pass

    context = DummyContext()
    feedback = DummyFeedback()

    _ = action.processAlgorithm(parameters, context, feedback)

    assert isfile(parameters["file_path"])


def test_collapse_links(folder_path):
    project = create_example(folder_path, "nauru")
    links_before = project.network.count_links()
    nodes_before = project.network.count_nodes()
    project.close()

    parameters = {"PROJECT_FOLDER": folder_path, "LINK_IDS": "903,1075"}

    action = CollapseLinks()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    _ = action.run(parameters, context, feedback)

    project = Project()
    project.open(folder_path)

    assert project.network.count_links() < links_before
    assert project.network.count_nodes() < nodes_before


def test_network_simplifier(folder_path):
    project = create_example(folder_path, "nauru")
    links_before = project.network.count_links()
    nodes_before = project.network.count_nodes()
    project.close()

    parameters = {"PROJECT_FOLDER": folder_path}

    action = NetworkSimplifier()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    _ = action.run(parameters, context, feedback)

    project = Project()
    project.open(folder_path)

    assert project.network.count_links() < links_before
    assert project.network.count_nodes() < nodes_before

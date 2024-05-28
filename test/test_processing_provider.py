import pytest
import re
import pandas as pd
import numpy as np
import sqlite3
from os.path import isfile, join
from os import makedirs
from shutil import copyfile
from shapely.geometry import Point
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.project import Project
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback
from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem
from qgis.core import QgsField
from PyQt5.QtCore import QVariant

from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe

from qaequilibrae.modules.processing_provider.provider import Provider
from qaequilibrae.modules.processing_provider.export_matrix import ExportMatrix
from qaequilibrae.modules.processing_provider.matrix_from_layer import MatrixFromLayer
from qaequilibrae.modules.processing_provider.project_from_layer import ProjectFromLayer
from qaequilibrae.modules.processing_provider.Add_connectors import AddConnectors
from qaequilibrae.modules.processing_provider.assign_from_yaml import TrafficAssignYAML
from qaequilibrae.modules.processing_provider.renumber_from_centroids import RenumberNodesFromCentroids


def qgis_app():
    qgs = QgsApplication([], False)
    qgs.initQgis()
    yield qgs
    qgs.exitQgis()


def load_layers(folder):
    path_to_gpkg = f"{folder}/SiouxFalls.gpkg"

    gpkg_links_layer = path_to_gpkg + "|layername=links"
    gpkg_nodes_layer = path_to_gpkg + "|layername=nodes"

    linkslayer = QgsVectorLayer(gpkg_links_layer, "Links layer", "ogr")
    nodeslayer = QgsVectorLayer(gpkg_nodes_layer, "Nodes layer", "ogr")

    if not linkslayer.isValid():
        print("Links layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(linkslayer)
        var = QgsProject.instance().mapLayersByName("Links layer")
        if not var[0].crs().isValid():
            crs = QgsCoordinateReferenceSystem("EPSG:4326")
            var[0].setCrs(crs)

    if not nodeslayer.isValid():
        print("Nodes layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(nodeslayer)
        var = QgsProject.instance().mapLayersByName("Nodes layer")
        if not var[0].crs().isValid():
            crs = QgsCoordinateReferenceSystem("EPSG:4326")
            var[0].setCrs(crs)


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
    action = ExportMatrix()

    parameters = {
        "src": f"test/data/SiouxFalls_project/matrices/{source_file}",
        "dst": folder_path,
        "output_format": format,
    }

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    assert isfile(result["Output"])


def test_matrix_from_layer(folder_path):
    makedirs(folder_path)

    df = pd.read_csv("test/data/SiouxFalls_project/SiouxFalls_od.csv")
    layer = layer_from_dataframe(df, "SiouxFalls_od")

    action = MatrixFromLayer()

    parameters = {
        "matrix_layer": layer,
        "origin": "O",
        "destination": "D",
        "value": "Ton",
        "file_name": "siouxfalls_od",
        "output_folder": folder_path,
        "matrix_name": "NAME_FOR_TEST",
        "matrix_description": "this is a description",
        "matrix_core": "MAT_CORE",
    }

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    _ = action.run(parameters, context, feedback)

    assert isfile(join(folder_path, f"{parameters['file_name']}.aem"))

    mat = AequilibraeMatrix()
    mat.load(join(folder_path, f"{parameters['file_name']}.aem"))

    info = mat.__dict__
    assert info["names"] == [parameters["matrix_core"]]
    assert parameters["matrix_name"].encode() in info["name"]
    assert parameters["matrix_description"].encode() in info["description"]
    assert info["zones"] == 24
    assert np.sum(info["matrix"][parameters["matrix_core"]][:, :]) == 360600


def test_project_from_layer(folder_path):
    makedirs(folder_path)
    copyfile("test/data/SiouxFalls_project/SiouxFalls.gpkg", f"{folder_path}/SiouxFalls.gpkg")

    load_layers(folder_path)
    action = ProjectFromLayer()

    linkslayer = QgsProject.instance().mapLayersByName("Links layer")[0]

    linkslayer.startEditing()
    field = QgsField("ltype", QVariant.String)
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
        "dst": folder_path,
        "project_name": "from_test",
    }

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.run(parameters, context, feedback)

    assert result[0]["Output"] == join(folder_path, parameters["project_name"])

    QgsProject.instance().removeMapLayer(linkslayer.id())

    project = Project()
    project.open(join(folder_path, parameters["project_name"]))

    assert project.network.count_links() == 76
    assert project.network.count_nodes() == 24


def test_add_centroid_connector(pt_no_feed):
    project = pt_no_feed.project
    project_folder = project.project_base_path

    nodes = project.network.nodes

    cnt = nodes.new_centroid(100_000)
    cnt.geometry = Point(-71.34, -29.95)
    cnt.save()

    action = AddConnectors()

    parameters = {"num_connectors": 3, "mode": "c", "project_path": project_folder}

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    assert result["Output"] == project_folder

    node_qry = "select count(node_id) from nodes where is_centroid=1"
    node_count = project.conn.execute(node_qry).fetchone()[0]
    assert node_count == 1

    link_qry = "select count(name) from links where name like 'centroid connector%'"
    link_count = project.conn.execute(link_qry).fetchone()[0]
    assert link_count == 3


def test_renumber_from_centroids(ae_with_project):
    project = ae_with_project.project
    project_folder = project.project_base_path

    copyfile("test/data/SiouxFalls_project/SiouxFalls.gpkg", f"{project_folder}/SiouxFalls.gpkg")

    load_layers(project_folder)

    nodeslayer = QgsProject.instance().mapLayersByName("Nodes layer")[0]

    nodeslayer.startEditing()
    for feat in nodeslayer.getFeatures():
        value = feat["id"] + 1000
        nodeslayer.changeAttributeValue(feat.id(), nodeslayer.fields().indexFromName("id"), value)

    nodeslayer.commitChanges()

    action = RenumberNodesFromCentroids()

    parameters = {"nodes": nodeslayer, "node_id": "id", "project_path": project_folder}

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.run(parameters, context, feedback)

    assert result[0]["Output"] == project_folder

    node_qry = "select node_id from nodes;"
    node_count = project.conn.execute(node_qry).fetchall()
    node_count = [n[0] for n in node_count]
    assert node_count == list(range(1001, 1025))


def test_assign_from_yaml(ae_with_project):
    folder = ae_with_project.project.project_base_path
    file_path = join(folder, "config.yml")

    assert isfile(file_path)

    string_to_replace = "path_to_project"

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    updated_content = re.sub(re.escape(string_to_replace), folder, content)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(updated_content)

    action = TrafficAssignYAML()

    parameters = {"conf_file": file_path}

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

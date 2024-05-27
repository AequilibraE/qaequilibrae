import pytest
import re
from os.path import isfile, join
from os import makedirs, listdir
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback
from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem

from qaequilibrae.modules.processing_provider.provider import Provider
from qaequilibrae.modules.processing_provider.export_matrix import ExportMatrix
from qaequilibrae.modules.processing_provider.matrix_from_layer import MatrixFromLayer
from qaequilibrae.modules.processing_provider.project_from_layer import ProjectFromLayer
from qaequilibrae.modules.processing_provider.Add_connectors import AddConnectors
from qaequilibrae.modules.processing_provider.assign_from_yaml import TrafficAssignYAML
from qaequilibrae.modules.processing_provider.renumber_from_centroids import RenumberFromCentroids


def qgis_app():
    qgs = QgsApplication([], False)
    qgs.initQgis()
    yield qgs
    qgs.exitQgis()


def load_layers():
    path_to_gpkg = "test/data/SiouxFalls_project/SiouxFalls.gpkg"

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
        "srcFile": f"test/data/SiouxFalls_project/matrices/{source_file}",
        "destFolder": folder_path,
        "outputformat": format,  # Assume .csv
    }

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    assert isfile(result["Output"])


@pytest.mark.skip("not working")
def test_matrix_from_layer():
    action = MatrixFromLayer()


# @pytest.mark.skip("not working")
def test_project_from_layer(folder_path):
    load_layers()
    makedirs(folder_path)
    action = ProjectFromLayer()

    parameters = {
        "links": "Links layer",
        "link_type": "link_type",
        "direction": "direction",
        "modes": "modes",
        "destFolder": folder_path,
        "project_name": "from_test",
    }

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    # assert isfile(result['Output'])
    print(result.__dict__)


def test_add_centroid_connector():
    action = AddConnectors()


def test_renumber_from_centroids():
    action = RenumberFromCentroids()


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

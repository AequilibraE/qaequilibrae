import sys
from os import makedirs
from os.path import isfile, join

import numpy as np
import pytest
from aequilibrae import Project
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.utils.create_example import create_example
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback, QgsProject

from qaequilibrae.modules.processing_provider.matrix_procedures.export_matrix import ExportMatrix
from qaequilibrae.modules.processing_provider.matrix_procedures.matrix_calculator import MatrixCalculator
from qaequilibrae.modules.processing_provider.matrix_procedures.trip_length_distribution import TripLengthDistribution
from qaequilibrae.modules.processing_provider.model_building.add_links_from_layer import AddLinksFromLayer
from qaequilibrae.modules.processing_provider.model_building.collapse_links import CollapseLinks
from qaequilibrae.modules.processing_provider.model_building.network_simplifier import NetworkSimplifier
from qaequilibrae.modules.processing_provider.provider import Provider
from .utilities import load_test_layer

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


@pytest.mark.parametrize("format", [0, 1])
def test_export_matrix(folder_path, format):
    makedirs(folder_path)

    parameters = {
        "matrix_path": "test/data/SiouxFalls_project/matrices/sfalls_skims.omx",
        "file_path": folder_path,
        "output_format": format,
    }

    action = ExportMatrix()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result = action.processAlgorithm(parameters, context, feedback)

    assert isfile(result["Output"])


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

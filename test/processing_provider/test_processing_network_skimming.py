import openmatrix as omx
import pytest
from aequilibrae.context import get_active_project
from qgis.core import QgsProcessingContext, QgsProcessingException, QgsProcessingFeedback

from qaequilibrae.modules.processing_provider.paths_procedures import network_skimming as operation
from qaequilibrae.modules.processing_provider.paths_procedures.network_skimming import NetworkSkimming
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm


def _parameters(project_path, **overrides):
    parameters = {
        ProjectAlgorithm.PROJECT_FOLDER: str(project_path),
        NetworkSkimming.MODE: "c",
        NetworkSkimming.COST_FIELD: "distance",
        NetworkSkimming.SKIM_FIELDS: "distance,free_flow_time",
        NetworkSkimming.TRACE_ALL_NODES: False,
        NetworkSkimming.BLOCK_CENTROID_FLOWS: False,
        NetworkSkimming.MATRIX_NAME: "processing_skims",
    }
    parameters.update(overrides)
    return parameters


def _run(parameters):
    """Run the algorithm, turning a captured Processing failure back into an exception."""
    algorithm = NetworkSkimming()
    algorithm.initAlgorithm()
    feedback = QgsProcessingFeedback()
    outputs, ok = algorithm.run(parameters, QgsProcessingContext(), feedback)
    if not ok:
        raise QgsProcessingException(feedback.textLog())
    return outputs


def test_network_skimming_runs_from_processing_parameters(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    outputs = _run(_parameters(project_path))

    assert outputs[NetworkSkimming.OUTPUT_MATRIX_NAME] == "processing_skims"
    with omx.open_file(outputs[NetworkSkimming.OUTPUT_MATRIX_PATH]) as matrix:
        assert set(matrix.list_matrices()) == {"distance", "free_flow_time"}
        assert matrix["distance"].shape[0] > 0


def test_network_skimming_registers_the_matrix_in_the_project(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    outputs = _run(_parameters(project_path))

    from aequilibrae import Project

    project = Project()
    project.open(project_path)
    try:
        assert "processing_skims" in project.matrices.list()["name"].tolist()
    finally:
        project.close()
    assert outputs[NetworkSkimming.OUTPUT_MATRIX_FOLDER]


def test_network_skimming_borrows_an_open_project_and_keeps_it_active(sf_project):
    project = sf_project.project
    outputs = operation.run_network_skimming(_parameters(project.project_base_path), project=project)

    assert get_active_project() is project
    assert outputs[NetworkSkimming.OUTPUT_MATRIX_NAME] == "processing_skims"


def test_network_skimming_can_trace_all_nodes(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    _run(_parameters(project_path, TRACE_ALL_NODES=True, BLOCK_CENTROID_FLOWS=False))


def test_network_skimming_rejects_blocked_flows_between_all_nodes(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    with pytest.raises(QgsProcessingException, match="all nodes"):
        _run(_parameters(project_path, TRACE_ALL_NODES=True, BLOCK_CENTROID_FLOWS=True))


def test_network_skimming_requires_at_least_one_skim_field(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    with pytest.raises(QgsProcessingException, match="skim field"):
        _run(_parameters(project_path, SKIM_FIELDS="  "))


def test_network_skimming_rejects_an_existing_matrix(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()
    _run(_parameters(project_path))

    with pytest.raises(QgsProcessingException, match="already exists"):
        _run(_parameters(project_path))


def test_network_skimming_parses_excluded_links(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    outputs = _run(_parameters(project_path, EXCLUDED_LINKS="4, 14"))
    assert outputs[NetworkSkimming.OUTPUT_MATRIX_NAME]


def test_network_skimming_rejects_non_integer_excluded_links(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    with pytest.raises(QgsProcessingException, match="integers"):
        _run(_parameters(project_path, EXCLUDED_LINKS="4,not-a-link"))


def test_network_skimming_reports_progress(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    algorithm = NetworkSkimming()
    algorithm.initAlgorithm()
    feedback = QgsProcessingFeedback()
    seen = []
    feedback.progressChanged.connect(seen.append)
    _, ok = algorithm.run(_parameters(project_path), QgsProcessingContext(), feedback)
    assert ok, feedback.textLog()
    assert seen
    assert seen[-1] == 100
    assert seen == sorted(seen)


def test_network_skimming_gives_the_project_record_a_description(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()
    _run(_parameters(project_path))

    from aequilibrae import Project

    project = Project()
    project.open(project_path)
    try:
        record = project.matrices.get_record("processing_skims")
        assert record.procedure == "Network skimming"
    finally:
        project.close()

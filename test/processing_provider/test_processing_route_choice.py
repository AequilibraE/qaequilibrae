import numpy as np
import pytest
from aequilibrae.context import get_active_project
from qgis.core import QgsProcessingContext, QgsProcessingException, QgsProcessingFeedback

from qaequilibrae.modules.processing_provider.paths_procedures.route_choice import (
    RouteChoice,
    _select_links,
    run_route_choice,
    run_single_route_choice,
)
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm
from test.utilities import create_matrix


def _parameters(project_path, **overrides):
    parameters = {
        ProjectAlgorithm.PROJECT_FOLDER: str(project_path),
        RouteChoice.MODE: "c",
        RouteChoice.UTILITY_FIELDS: [0.01, "distance"],
        RouteChoice.ALGORITHM: "bfsle",
        RouteChoice.MAX_ROUTES: 3,
        RouteChoice.MAX_DEPTH: 0,
        RouteChoice.PENALTY: 1.0,
        RouteChoice.CUTOFF: 0.0,
        RouteChoice.BETA: 1.1,
        RouteChoice.BLOCK_CENTROID_FLOWS: False,
        RouteChoice.MATRIX_NAME: "demand_omx",
        RouteChoice.MATRIX_CORES: "matrix",
        RouteChoice.JOB: "assign",
        RouteChoice.RESULT_NAME: "processing_route_choice",
        RouteChoice.SAVE_CHOICE_SETS: False,
        RouteChoice.EXCLUDED_LINKS: "",
        RouteChoice.SELECT_LINKS: [],
        RouteChoice.SELECT_LINK_NAME: "processing_route_choice_sl",
        RouteChoice.SUB_AREA: False,
    }
    parameters.update(overrides)
    return parameters


def test_route_choice_runs_from_processing_parameters(sf_project):
    project = sf_project.project
    project_path = project.project_base_path
    project.close()
    algorithm = RouteChoice()
    algorithm.initAlgorithm()
    feedback = QgsProcessingFeedback()
    outputs, ok = algorithm.run(
        _parameters(project_path),
        QgsProcessingContext(),
        feedback,
    )

    assert ok, feedback.textLog()
    assert outputs[RouteChoice.OUTPUT_RESULT_NAME] == "processing_route_choice_uncompressed"


def test_route_choice_assignment_runs_as_processing_operation(sf_project):
    project = sf_project.project
    outputs = run_route_choice(_parameters(project.project_base_path), project=project)

    assert outputs[RouteChoice.OUTPUT_RESULT_NAME] == "processing_route_choice_uncompressed"
    with project.results_connection as connection:
        assert connection.execute("SELECT COUNT(*) FROM processing_route_choice_uncompressed").fetchone()[0] > 0
    assert get_active_project() is project


def test_single_route_choice_uses_shared_graph_without_changing_project(sf_project):
    project = sf_project.project
    project.network.build_graphs(modes=["c"])
    original_graph = project.network.graphs["c"]
    configuration = {
        "mode": "c",
        "utility_fields": [(0.01, "distance")],
        "excluded_links": [],
        "block_centroid_flows": False,
        "algorithm": "bfsle",
        "kwargs": {"max_routes": 3, "max_depth": 0, "penalty": 1.0, "cutoff_prob": 0.0, "beta": 1.1},
    }

    choice, graph = run_single_route_choice(project, configuration, 1, 15, 1.0)

    assert not choice.get_results().empty
    assert graph is not original_graph
    assert "__utility__" not in original_graph.network.columns
    assert get_active_project() is project


def test_route_choice_build_saves_choice_sets(sf_project):
    project = sf_project.project
    parameters = _parameters(
        project.project_base_path,
        JOB="build",
        RESULT_NAME="processing_route_build",
    )

    outputs = run_route_choice(parameters, project=project)

    assert outputs[RouteChoice.OUTPUT_ROUTES_FOLDER] == str(project.project_base_path / "route_choice")
    assert (project.project_base_path / "route_choice").is_dir()


def test_route_choice_saves_select_link_outputs(coquimbo_project):
    project = coquimbo_project.project
    matrix_path = project.project_base_path / "matrices" / "demand.omx"
    create_matrix(np.arange(1, 134), matrix_path)
    project.matrices.update_database()
    project.matrices.reload()
    parameters = _parameters(
        project.project_base_path,
        MATRIX_NAME="demand_omx",
        MATRIX_CORES="demand",
        SELECT_LINKS=["bridge", "7369:AB,20983:AB"],
        SELECT_LINK_NAME="processing_route_sl.v1",
    )

    outputs = run_route_choice(parameters, project=project)

    assert outputs[RouteChoice.OUTPUT_SELECT_LINK_FLOWS] == "processing_route_sl.v1_uncompressed"
    matrix_path = project.project_base_path / "matrices" / "processing_route_sl.v1.omx"
    assert outputs[RouteChoice.OUTPUT_SELECT_LINK_MATRIX] == str(matrix_path)
    assert matrix_path.is_file()


def test_route_choice_does_not_overwrite_legacy_select_link_matrix(sf_project):
    project = sf_project.project
    existing_matrix = project.project_base_path / "matrices" / "processing_route_sl.omx"
    existing_matrix.write_bytes(b"existing matrix")
    parameters = _parameters(
        project.project_base_path,
        SELECT_LINKS=["bridge", "1:AB"],
        SELECT_LINK_NAME="processing_route_sl.v1",
    )

    with pytest.raises(QgsProcessingException, match="already exists"):
        run_route_choice(parameters, project=project)

    assert existing_matrix.read_bytes() == b"existing matrix"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"MATRIX_CORES": "missing_core"}, "does not contain"),
        ({"UTILITY_FIELDS": [1.0, "missing_field"]}, "not available"),
        ({"EXCLUDED_LINKS": "invalid"}, "must be integers"),
    ],
)
def test_route_choice_invalid_inputs_leave_no_results(sf_project, overrides, message):
    project = sf_project.project
    parameters = _parameters(project.project_base_path, **overrides)
    with pytest.raises(QgsProcessingException, match=message):
        run_route_choice(parameters, project=project)

    with project.results_connection as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name = 'processing_route_choice_uncompressed'"
        ).fetchone()[0] == 0


def test_route_choice_cancellation_does_not_write_outputs(sf_project):
    project = sf_project.project
    feedback = QgsProcessingFeedback()
    feedback.cancel()
    with pytest.raises(QgsProcessingException, match="canceled"):
        run_route_choice(_parameters(project.project_base_path), project=project, feedback=feedback)

    with project.results_connection as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name = 'processing_route_choice_uncompressed'"
        ).fetchone()[0] == 0
    assert not (project.project_base_path / "route_choice").exists()


def test_route_choice_cancellation_after_compute_does_not_save(sf_project, monkeypatch):
    from aequilibrae.paths import RouteChoice as AequilibraeRouteChoice

    project = sf_project.project
    feedback = QgsProcessingFeedback()
    execute = AequilibraeRouteChoice.execute

    def cancel_after_compute(self, *args, **kwargs):
        result = execute(self, *args, **kwargs)
        feedback.cancel()
        return result

    monkeypatch.setattr(AequilibraeRouteChoice, "execute", cancel_after_compute)
    with pytest.raises(QgsProcessingException, match="canceled"):
        run_route_choice(_parameters(project.project_base_path), project=project, feedback=feedback)

    with project.results_connection as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name = 'processing_route_choice_uncompressed'"
        ).fetchone()[0] == 0


def test_route_choice_rejects_an_existing_result(sf_project):
    project = sf_project.project
    parameters = _parameters(project.project_base_path)
    run_route_choice(parameters, project=project)

    with pytest.raises(QgsProcessingException, match="already exists"):
        run_route_choice(parameters, project=project)


def test_route_choice_parses_select_link_sets():
    assert _select_links(["bridge", "1:AB,2:BA", "bridge", "3:Both"]) == {"bridge": [[(1, 1), (2, -1)], [(3, 0)]]}


def test_route_choice_rejects_bad_select_link_direction():
    with pytest.raises(ValueError, match="direction"):
        _select_links(["bridge", "1:sideways"])

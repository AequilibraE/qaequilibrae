import json
from pathlib import Path

import numpy as np
import openmatrix as omx
import pytest
from aequilibrae.context import get_active_project
from qgis.core import (
    QgsApplication,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsProcessingModelAlgorithm,
    QgsProcessingModelChildAlgorithm,
    QgsProcessingModelChildParameterSource,
    QgsProcessingModelOutput,
)

from qaequilibrae.modules.processing_provider.paths_procedures.traffic_assignment import RunTrafficAssignment
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm
from qaequilibrae.modules.processing_provider.paths_procedures import traffic_assignment as operation


def test_traffic_assignment_runs_from_processing_parameters(sf_project):
    project_path = sf_project.project.project_base_path
    sf_project.project.close()

    algorithm = RunTrafficAssignment()
    algorithm.initAlgorithm()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    result, succeeded = algorithm.run(
        {
            ProjectAlgorithm.PROJECT_FOLDER: str(project_path),
            RunTrafficAssignment.TRAFFIC_CLASSES: [
                "car",
                "demand",
                "matrix",
                "c",
                1.0,
                False,
                "",
                "",
                "",
            ],
            RunTrafficAssignment.ALGORITHM: "bfw",
            RunTrafficAssignment.MAX_ITERATIONS: 5,
            RunTrafficAssignment.RELATIVE_GAP: 0.001,
            RunTrafficAssignment.VDF: "bpr",
            RunTrafficAssignment.ALPHA: 0.15,
            RunTrafficAssignment.BETA: 4.0,
            RunTrafficAssignment.CAPACITY_FIELD: "capacity",
            RunTrafficAssignment.TIME_FIELD: "free_flow_time",
            RunTrafficAssignment.RESULT_NAME: "processing_assignment",
        },
        context,
        feedback,
    )

    assert succeeded, feedback.textLog()
    assert result[RunTrafficAssignment.OUTPUT_RESULT_NAME] == "processing_assignment"
    assert "Saved traffic-assignment results" in feedback.textLog()


def _parameters(project):
    return {
        RunTrafficAssignment.PROJECT_FOLDER: str(project.project_base_path),
        RunTrafficAssignment.TRAFFIC_CLASSES: ["car", "demand", "matrix", "c", 1.0, False, "", "", ""],
        RunTrafficAssignment.MAX_ITERATIONS: 3,
        RunTrafficAssignment.RESULT_NAME: "processing_assignment",
    }


def _run(parameters):
    algorithm = RunTrafficAssignment()
    algorithm.initAlgorithm()
    feedback = QgsProcessingFeedback()
    outputs, ok = algorithm.run(parameters, QgsProcessingContext(), feedback)
    assert ok, feedback.textLog()
    return outputs


def test_assignment_reports_progress(sf_project):
    algorithm = RunTrafficAssignment()
    algorithm.initAlgorithm()
    feedback = QgsProcessingFeedback()
    seen = []
    feedback.progressChanged.connect(seen.append)
    _, ok = algorithm.run(_parameters(sf_project.project), QgsProcessingContext(), feedback)
    assert ok, feedback.textLog()
    assert seen
    assert seen[-1] == 100
    assert seen == sorted(seen)


@pytest.mark.parametrize("save_matrix,save_flows", [(True, True), (True, False), (False, True), (False, False)])
def test_select_link_outputs_and_skim_choices(sf_project, save_matrix, save_flows):
    project = sf_project.project
    parameters = _parameters(project)
    parameters[RunTrafficAssignment.TRAFFIC_CLASSES][-1] = "free_flow_time:final,distance:blended"
    parameters.update(
        {
            RunTrafficAssignment.SELECT_LINKS: ["bridge", "1", "AB", "bridge", "2", "AB"],
            RunTrafficAssignment.SAVE_SELECT_LINK_MATRICES: save_matrix,
            RunTrafficAssignment.SAVE_SELECT_LINK_FLOWS: save_flows,
        }
    )
    outputs = _run(parameters)
    assert get_active_project() is project
    assert Path(outputs[RunTrafficAssignment.OUTPUT_DATABASE]).is_file()
    assert Path(outputs[RunTrafficAssignment.OUTPUT_MATRIX_FOLDER]).is_dir()
    skim_paths = json.loads(outputs[RunTrafficAssignment.OUTPUT_SKIMS])
    assert len(skim_paths) == 1
    with omx.open_file(skim_paths[0]) as matrix:
        assert set(matrix.list_matrices()) == {"free_flow_time_final", "distance_blended"}
        assert np.nansum(matrix["distance_blended"][:]) > 0
    matrix_path = outputs[RunTrafficAssignment.OUTPUT_SELECT_LINK_MATRIX]
    if save_matrix:
        with omx.open_file(matrix_path) as matrix:
            assert matrix.list_matrices() == ["bridge_car"]
            assert np.nansum(matrix["bridge_car"][:]) > 0
    else:
        assert matrix_path == ""
        assert not (project.project_base_path / "matrices/processing_assignment_sl.omx").exists()
    flow_table = outputs[RunTrafficAssignment.OUTPUT_SELECT_LINK_FLOWS]
    with project.results_connection as connection:
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE name='processing_assignment_sl'").fetchone()
        assert bool(exists) == save_flows
        if save_flows:
            assert flow_table == "processing_assignment_sl"
            assert connection.execute(f'SELECT COUNT(*) FROM "{flow_table}"').fetchone()[0] > 0
        else:
            assert flow_table == ""


def test_multicore_select_link_preserves_each_demand_core(sf_project):
    parameters = _parameters(sf_project.project)
    parameters[RunTrafficAssignment.TRAFFIC_CLASSES] = [
        "car",
        "demand_mc",
        "car,motorcycle",
        "c",
        1.0,
        False,
        "",
        "",
        "distance",
    ]
    parameters[RunTrafficAssignment.SELECT_LINKS] = ["bridge", "1", "AB"]
    outputs = _run(parameters)
    with omx.open_file(outputs[RunTrafficAssignment.OUTPUT_SELECT_LINK_MATRIX]) as matrix:
        assert set(matrix.list_matrices()) == {"bridge_car_car", "bridge_car_motorcycle"}
        car = matrix["bridge_car_car"][:]
        motorcycle = matrix["bridge_car_motorcycle"][:]
        assert car.sum() > 0
        assert motorcycle.sum() > 0
        assert not np.allclose(car, motorcycle)


@pytest.mark.parametrize("failure", ["setup", "save"])
def test_failure_closes_input_matrices_and_preserves_borrowed_project(sf_project, mocker, failure):
    project = sf_project.project
    parameters = _parameters(project)
    matrix = operation._matrix(project, "demand")
    close = mocker.spy(matrix, "close")
    mocker.patch.object(operation, "_matrix", return_value=matrix)
    if failure == "setup":
        parameters[RunTrafficAssignment.TRAFFIC_CLASSES][2] = "missing_core"
    else:
        mocker.patch("aequilibrae.paths.TrafficAssignment.save_results", side_effect=OSError("disk full"))
    with pytest.raises(QgsProcessingException):
        operation.run_traffic_assignment(parameters, project=project)
    close.assert_called_once()
    assert get_active_project() is project
    with project.db_connection as connection:
        assert connection.execute("SELECT COUNT(*) FROM links").fetchone()[0] > 0


def test_existing_output_is_rejected_before_execution(sf_project, mocker):
    parameters = _parameters(sf_project.project)
    outputs = _run(parameters)
    execute = mocker.patch("aequilibrae.paths.TrafficAssignment.execute")
    with pytest.raises(QgsProcessingException, match="already exists"):
        operation.run_traffic_assignment(parameters, project=sf_project.project)
    execute.assert_not_called()
    assert Path(outputs[RunTrafficAssignment.OUTPUT_DATABASE]).is_file()


def test_cancel_after_computation_does_not_save(sf_project, mocker):
    feedback = QgsProcessingFeedback()
    mocker.patch("aequilibrae.paths.TrafficAssignment.execute", side_effect=feedback.cancel)
    save = mocker.patch("aequilibrae.paths.TrafficAssignment.save_results")
    with pytest.raises(QgsProcessingException, match="canceled"):
        operation.run_traffic_assignment(_parameters(sf_project.project), project=sf_project.project, feedback=feedback)
    save.assert_not_called()


def test_generated_result_field_collisions_are_rejected(sf_project):
    parameters = _parameters(sf_project.project)
    parameters[RunTrafficAssignment.TRAFFIC_CLASSES] = [
        "car",
        "demand_mc",
        "car,motorcycle",
        "c",
        1,
        False,
        "",
        "",
        "",
        "CAR_CAR",
        "demand",
        "matrix",
        "c",
        1,
        False,
        "",
        "",
        "",
    ]
    with pytest.raises(QgsProcessingException, match="Repeated result field"):
        operation.run_traffic_assignment(parameters, project=sf_project.project)


def test_select_link_rows_keep_mixed_directions():
    assert operation._select_links(["bridge", "1,2", "AB", "bridge", "3", "BA"]) == {
        "bridge": [(1, 1), (2, 1), (3, -1)],
    }


@pytest.fixture
def assignment_provider():
    from qaequilibrae.modules.processing_provider.provider import Provider

    registry = QgsApplication.processingRegistry()
    provider = Provider()
    assert registry.addProvider(provider)
    yield provider
    registry.removeProvider(provider)


def test_model_can_pass_select_link_matrix_to_export(sf_project, tmp_path, assignment_provider):
    """A saved model connects the assignment's file output to the existing exporter."""
    source = QgsProcessingModelChildParameterSource
    model = QgsProcessingModelAlgorithm()
    assignment = QgsProcessingModelChildAlgorithm()
    assignment.setChildId("assignment")
    assignment.setAlgorithmId("qaequilibrae:traffic_assignment")
    parameters = _parameters(sf_project.project)
    parameters[RunTrafficAssignment.SELECT_LINKS] = ["bridge", "1", "AB"]
    for key, value in parameters.items():
        assignment.addParameterSources(key, [source.fromStaticValue(value)])
    output = QgsProcessingModelOutput("SELECT_LINK_MATRIX", "Select-link matrix")
    output.setChildId("assignment")
    output.setChildOutputName(RunTrafficAssignment.OUTPUT_SELECT_LINK_MATRIX)
    assignment.setModelOutputs({"SELECT_LINK_MATRIX": output})
    model.addChildAlgorithm(assignment)

    export = QgsProcessingModelChildAlgorithm()
    export.setChildId("export")
    export.setAlgorithmId("qaequilibrae:exportmatrices")
    export.addParameterSources(
        "matrix_path", [source.fromChildOutput("assignment", RunTrafficAssignment.OUTPUT_SELECT_LINK_MATRIX)]
    )
    export.addParameterSources("file_path", [source.fromStaticValue(str(tmp_path))])
    export.addParameterSources("output_format", [source.fromStaticValue(0)])
    model.addChildAlgorithm(export)
    model.updateDestinationParameters()
    restored = QgsProcessingModelAlgorithm()
    assert restored.loadVariant(model.toVariant())
    feedback = QgsProcessingFeedback()
    _, ok = restored.run({}, QgsProcessingContext(), feedback)
    assert ok, feedback.textLog()
    csv_path = tmp_path / "processing_assignment_sl.csv"
    assert csv_path.is_file()
    assert "bridge_car" in csv_path.read_text().splitlines()[0]

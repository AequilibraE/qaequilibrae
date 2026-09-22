from qgis.core import QgsProcessingContext, QgsProcessingFeedback

from qaequilibrae.modules.processing_provider.paths_procedures.traffic_assignment import RunTrafficAssignment
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm


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

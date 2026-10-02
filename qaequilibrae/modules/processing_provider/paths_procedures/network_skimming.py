"""Network-skimming computation and its QGIS Processing adapter."""

from pathlib import Path
from typing import Any, TypedDict

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputFile,
    QgsProcessingOutputFolder,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterString,
)

from ..feedback import connect_progress, push_info
from ..project import borrow_project
from ..project_algorithm import ProjectAlgorithm


class SkimmingError(ValueError):
    """An invalid network-skimming configuration."""


class SkimmingConfiguration(TypedDict):
    """Validated settings for one network-skimming run."""

    mode: str
    cost_field: str
    skim_fields: list[str]
    block_centroid_flows: bool
    trace_all_nodes: bool
    excluded_links: list[int]
    matrix_name: str


def run_network_skimming(
    parameters: dict[str, Any],
    project: Any | None = None,
    feedback: QgsProcessingFeedback | None = None,
) -> dict[str, str]:
    """Run network skimming from Processing parameters and an optional open project."""
    algorithm = NetworkSkimming()
    algorithm.initAlgorithm()
    algorithm.project = project
    return algorithm.processAlgorithm(parameters, QgsProcessingContext(), feedback or QgsProcessingFeedback())


def _run_skimming(
    project_folder: Any,
    configuration: SkimmingConfiguration,
    feedback: QgsProcessingFeedback | None,
) -> dict[str, str]:
    from aequilibrae.paths import NetworkSkimming as SkimmingProcedure

    push_info(feedback, "Opening AequilibraE project")
    with borrow_project(project_folder) as project:
        _check_canceled(feedback)
        _check_output_names(project, configuration)
        mode = configuration["mode"]
        project.network.build_graphs(modes=[mode])
        graph = project.network.graphs[mode]
        if configuration["trace_all_nodes"]:
            graph.prepare_graph(graph.all_nodes)
        graph.set_graph(configuration["cost_field"])
        graph.set_blocked_centroid_flows(configuration["block_centroid_flows"])
        if configuration["excluded_links"]:
            graph.exclude_links(configuration["excluded_links"])
        graph.set_skimming(configuration["skim_fields"])

        skimming = SkimmingProcedure(graph)
        connect_progress(skimming, feedback)
        push_info(feedback, "Running network skimming")
        skimming.execute()
        if skimming.report:
            push_info(feedback, "\n".join(skimming.report))
        _check_canceled(feedback)
        push_info(feedback, "Saving network skim matrix")
        matrix_name = configuration["matrix_name"]
        skimming.save_to_project(matrix_name, project=project)
        matrix_path = Path(project.matrices.fldr) / f"{matrix_name}.omx"

    push_info(feedback, f"Saved network skim matrix as {matrix_name}")
    return {
        NetworkSkimming.OUTPUT_MATRIX_NAME: matrix_name,
        NetworkSkimming.OUTPUT_MATRIX_PATH: str(matrix_path),
        NetworkSkimming.OUTPUT_MATRIX_FOLDER: str(matrix_path.parent),
    }


def _check_canceled(feedback: QgsProcessingFeedback | None) -> None:
    if feedback is not None and feedback.isCanceled():
        raise SkimmingError("Network skimming canceled; results were not saved")


def _check_output_names(project: Any, configuration: SkimmingConfiguration) -> None:
    name = configuration["matrix_name"]
    if Path(name).name != name or "\\" in name:
        raise SkimmingError("Matrix names must not contain directory separators")
    if project.matrices.check_exists(name) or (Path(project.matrices.fldr) / f"{name}.omx").exists():
        raise SkimmingError(f"Matrix '{name}' already exists")


class NetworkSkimming(ProjectAlgorithm):
    """Compute a network skim matrix for one mode."""

    algorithm_name = "network_skimming"
    display_name = "Network skimming"
    group_name = "Path computation"
    group_id = "path_computation"

    MODE = "MODE"
    COST_FIELD = "COST_FIELD"
    SKIM_FIELDS = "SKIM_FIELDS"
    BLOCK_CENTROID_FLOWS = "BLOCK_CENTROID_FLOWS"
    TRACE_ALL_NODES = "TRACE_ALL_NODES"
    EXCLUDED_LINKS = "EXCLUDED_LINKS"
    MATRIX_NAME = "MATRIX_NAME"
    OUTPUT_MATRIX_NAME = "OUTPUT_MATRIX_NAME"
    OUTPUT_MATRIX_PATH = "OUTPUT_MATRIX_PATH"
    OUTPUT_MATRIX_FOLDER = "OUTPUT_MATRIX_FOLDER"
    project: Any | None = None

    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        self.add_project_folder_parameter()
        self.addParameter(QgsProcessingParameterString(self.MODE, self.tr("Network mode")))
        self.addParameter(QgsProcessingParameterString(self.COST_FIELD, self.tr("Cost field"), "distance"))
        self.addParameter(
            QgsProcessingParameterString(
                self.SKIM_FIELDS,
                self.tr("Skim fields (comma-separated)"),
                defaultValue="distance",
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.TRACE_ALL_NODES,
                self.tr("Trace between all nodes"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.BLOCK_CENTROID_FLOWS,
                self.tr("Block flows through centroids"),
                defaultValue=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.EXCLUDED_LINKS,
                self.tr("Excluded link IDs (comma-separated)"),
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterString(self.MATRIX_NAME, self.tr("Output matrix name"), "skims"))
        self.addOutput(QgsProcessingOutputString(self.OUTPUT_MATRIX_NAME, self.tr("Matrix name")))
        self.addOutput(QgsProcessingOutputFile(self.OUTPUT_MATRIX_PATH, self.tr("Matrix file")))
        self.addOutput(QgsProcessingOutputFolder(self.OUTPUT_MATRIX_FOLDER, self.tr("Matrix folder")))

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, str]:
        try:
            configuration = self._configuration(parameters, context)
            project_folder = self.project or self.project_folder(parameters, context)
            return _run_skimming(project_folder, configuration, feedback)
        except Exception as error:
            raise QgsProcessingException(self.tr(str(error))) from error

    def _configuration(self, parameters: dict[str, Any], context: QgsProcessingContext) -> SkimmingConfiguration:
        mode = self.parameterAsString(parameters, self.MODE, context).strip()
        if not mode:
            raise SkimmingError("A network mode is required")
        cost_field = self.parameterAsString(parameters, self.COST_FIELD, context).strip()
        if not cost_field:
            raise SkimmingError("A cost field is required")

        raw_fields = self.parameterAsString(parameters, self.SKIM_FIELDS, context)
        skim_fields = [field.strip() for field in raw_fields.split(",") if field.strip()]
        if not skim_fields:
            raise SkimmingError("At least one skim field is required")

        block_centroid_flows = self.parameterAsBool(parameters, self.BLOCK_CENTROID_FLOWS, context)
        trace_all_nodes = self.parameterAsBool(parameters, self.TRACE_ALL_NODES, context)
        if trace_all_nodes and block_centroid_flows:
            raise SkimmingError(
                "It is not possible to trace paths between all nodes while blocking flows through centroids"
            )

        matrix_name = self.parameterAsString(parameters, self.MATRIX_NAME, context).strip()
        if not matrix_name:
            raise SkimmingError("An output matrix name is required")

        raw_links = self.parameterAsString(parameters, self.EXCLUDED_LINKS, context)
        try:
            excluded_links = [int(link_id.strip()) for link_id in raw_links.split(",") if link_id.strip()]
        except ValueError as error:
            raise SkimmingError("Excluded link IDs must be integers separated by commas") from error

        return {
            "mode": mode,
            "cost_field": cost_field,
            "skim_fields": skim_fields,
            "block_centroid_flows": block_centroid_flows,
            "trace_all_nodes": trace_all_nodes,
            "excluded_links": excluded_links,
            "matrix_name": matrix_name,
        }

    def shortHelpString(self) -> str:
        help_messages = [
            self.tr("Skims a mode's network and saves the result as a matrix in the AequilibraE project."),
            self.tr("Inputs:"),
            self.tr("- AequilibraE project folder: the project whose network is skimmed."),
            self.tr("- Network mode and the cost field the paths are minimised on."),
            self.tr("- Skim fields: the network fields written to the matrix, comma-separated."),
            self.tr(
                "- Trace between all nodes: skim every node instead of only the network's centroids. "
                "This cannot be combined with blocking flows through centroids."
            ),
            self.tr(
                "- Block flows through centroids: keep centroid-to-centroid paths from passing through another centroid."
            ),
            self.tr("- Excluded link IDs (optional): links left out of the graph, comma-separated."),
            self.tr("- Output matrix name: name of the OMX matrix and its project record."),
            self.tr("Outputs:"),
            self.tr("- Matrix name, matrix file and matrix folder for use by later steps."),
            self.tr("Existing matrix names are not overwritten."),
        ]
        return "\n".join(help_messages)

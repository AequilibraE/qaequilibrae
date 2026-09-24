"""Route-choice Processing operation shared by the dialog and project runners.

The module builds a mode graph from weighted network fields, applies demand from
project matrices, and optionally saves route sets, assignment results, select-link
outputs, or sub-area demand. :func:`run_route_choice` also lets the desktop dialog
reuse the same operation without reopening its project.
"""

from collections.abc import Hashable, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any, TypedDict, cast

import geopandas as gpd
import numpy as np
from qgis.core import (
    Qgis,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputFile,
    QgsProcessingOutputFolder,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.common_tools import geodataframe_from_layer, model_area_polygon

from ..project import borrow_project
from ..project_algorithm import ProjectAlgorithm


class RouteChoiceError(ValueError):
    """An invalid route-choice configuration."""


class RouteChoiceConfiguration(TypedDict):
    """Validated settings for a route-choice assignment or build."""

    mode: str
    utility_fields: list[tuple[float, str]]
    algorithm: str
    kwargs: dict[str, Any]
    block_centroid_flows: bool
    matrix_name: str
    matrix_cores: list[str]
    job: str
    output_name: str
    save_choice_sets: bool
    excluded_links: list[int]
    select_links: dict[str, list[tuple[int, int] | list[tuple[int, int]]]]
    select_link_name: str
    sub_area: bool


def run_route_choice(
    parameters: dict[str, Any],
    project: Any | None = None,
    feedback: QgsProcessingFeedback | None = None,
    zones: Any | None = None,
) -> dict[str, str]:
    """Run the Processing worker from the dialog or a project runner.

    Args:
        parameters: Processing inputs for the project, graph, demand, algorithm, and outputs.
        project: An already-open AequilibraE project. If omitted, the worker opens the
            folder from ``parameters`` and restores the previously active project.
        feedback: Optional Processing feedback for messages, progress, and cancellation.
        zones: Optional polygon GeoDataFrame used by the dialog's sub-area workflow.

    Returns:
        Fixed-name outputs for result tables, saved choice sets, and optional matrices.

    Raises:
        QgsProcessingException: If configuration, computation, or output saving fails.
    """
    algorithm = RouteChoice()
    algorithm.initAlgorithm()
    algorithm.project = project
    algorithm.zones = zones
    return algorithm.processAlgorithm(parameters, QgsProcessingContext(), feedback or QgsProcessingFeedback())


def _run_route_choice(
    project_or_folder: Any,
    configuration: RouteChoiceConfiguration,
    zones_layer: Any | None,
    feedback: QgsProcessingFeedback | None,
) -> dict[str, str]:
    """Run route choice, save configured outputs, and return their paths or names."""
    _info(feedback, "Opening AequilibraE project")
    with borrow_project(project_or_folder) as project:
        _check_canceled(feedback)
        matrix_name = configuration["matrix_name"]
        output_name = configuration["output_name"]
        routes_folder = Path(project.project_base_path) / "route_choice"
        _check_output_names(project, configuration, routes_folder)

        demand_matrix = _load_demand(project, matrix_name, configuration["matrix_cores"])
        matrix = demand_matrix
        try:
            graph = _build_utility_graph(project, configuration)
            if configuration["sub_area"]:
                if zones_layer is None:
                    raise RouteChoiceError("A polygon layer is required for sub-area analysis")
                zones_data = zones_layer if hasattr(zones_layer, "to_crs") else geodataframe_from_layer(zones_layer)
                polygon, crs = model_area_polygon(zones_data)
                zones = gpd.GeoDataFrame(geometry=[polygon], crs=crs)
                routes_folder.mkdir(parents=True, exist_ok=True)
                from aequilibrae.paths import SubAreaAnalysis

                sub_area = SubAreaAnalysis(graph, zones, matrix)
                sub_area.rc.set_choice_set_generation(configuration["algorithm"], **configuration["kwargs"])
                _info(feedback, "Running sub-area route-choice analysis")
                sub_area.rc.execute(True)
                sub_area_matrix = sub_area.post_process().reset_index().infer_objects()
                sub_area_matrix = sub_area_matrix.groupby(["origin id", "destination id"]).sum()
                sub_area_matrix.to_parquet(routes_folder / f"{output_name}.parquet")
                nodes = np.unique(sub_area_matrix.reset_index()[["origin id", "destination id"]].to_numpy().reshape(-1))
                graph.prepare_graph(nodes)
                graph.set_graph("__utility__")
                matrix = sub_area_matrix

            from aequilibrae.paths import RouteChoice as AequilibraERouteChoice

            route_choice = AequilibraERouteChoice(graph, project=project)
            route_choice.set_choice_set_generation(configuration["algorithm"], **configuration["kwargs"])
            route_choice.add_demand(matrix)
            route_choice.prepare()
            if configuration["select_links"]:
                selections = cast(
                    dict[Hashable, list[tuple[int, int] | list[tuple[int, int]]]],
                    configuration["select_links"],
                )
                route_choice.set_select_links(selections)
            if configuration["job"] == "build" or configuration["save_choice_sets"]:
                routes_folder.mkdir(parents=True, exist_ok=True)
                route_choice.set_save_routes(str(routes_folder))
            _report_progress(route_choice, feedback)
            _check_canceled(feedback)
            _info(
                feedback, "Building route choice sets" if configuration["job"] == "build" else "Assigning route choice"
            )
            route_choice.execute(configuration["job"] == "assign")
            _check_canceled(feedback)

            outputs = {
                RouteChoice.OUTPUT_RESULT_NAME: "",
                RouteChoice.OUTPUT_ROUTES_FOLDER: str(routes_folder)
                if configuration["job"] == "build" or configuration["save_choice_sets"]
                else "",
                RouteChoice.OUTPUT_SUB_AREA_MATRIX: str(routes_folder / f"{output_name}.parquet")
                if configuration["sub_area"]
                else "",
                RouteChoice.OUTPUT_SELECT_LINK_FLOWS: "",
                RouteChoice.OUTPUT_SELECT_LINK_MATRIX: "",
            }
            if configuration["job"] == "assign":
                route_choice.save_link_flows(output_name, project=project)
                outputs[RouteChoice.OUTPUT_RESULT_NAME] = f"{output_name}_uncompressed"
            if configuration["select_links"]:
                route_choice.save_select_link_flows(configuration["select_link_name"], project=project)
                outputs[RouteChoice.OUTPUT_SELECT_LINK_FLOWS] = f"{configuration['select_link_name']}_uncompressed"
                outputs[RouteChoice.OUTPUT_SELECT_LINK_MATRIX] = str(
                    (Path(project.matrices.fldr) / configuration["select_link_name"]).with_suffix(".omx")
                )
        finally:
            demand_matrix.close()

    _info(feedback, "Route-choice operation completed")
    return outputs


def _load_demand(project: Any, matrix_name: str, cores: list[str]) -> Any:
    """Load a project demand matrix and set its computational cores."""
    try:
        matrix = project.matrices.get_matrix(matrix_name)
    except Exception as error:
        raise RouteChoiceError(f"Could not load demand matrix '{matrix_name}': {error}") from error
    try:
        if not cores or any(core not in matrix.names for core in cores):
            raise RouteChoiceError(f"Demand matrix '{matrix_name}' does not contain the requested core(s)")
        matrix.computational_view(cores)
        return matrix
    except Exception:
        matrix.close()
        raise


def _build_utility_graph(project: Any, configuration: RouteChoiceConfiguration) -> Any:
    """Build an isolated mode graph and calculate its weighted utility field."""
    mode = configuration["mode"]
    project.network.build_graphs(modes=[mode])
    graph = deepcopy(project.network.graphs[mode])
    graph.network = graph.network.assign(__utility__=0.0)
    if configuration["excluded_links"]:
        graph.exclude_links(configuration["excluded_links"])
    graph.prepare_graph(graph.centroids)

    utility = np.zeros((1, graph.graph.shape[0]))
    for coefficient, field in configuration["utility_fields"]:
        if field not in graph.graph:
            raise RouteChoiceError(f"Utility field '{field}' is not available in the mode graph")
        utility += coefficient * graph.graph[field].array
    graph.graph["__utility__"] = utility.reshape(graph.graph.shape[0], 1)
    graph.set_blocked_centroid_flows(configuration["block_centroid_flows"])
    graph.set_graph("__utility__")
    return graph


def _report_progress(route_choice: Any, feedback: QgsProcessingFeedback | None) -> None:
    """Forward route-choice progress signals to Processing feedback."""
    signal = getattr(route_choice, "signal", None)
    if feedback is None or signal is None or not hasattr(signal, "connect"):
        return
    total = [1]

    def report(message: list[Any]) -> None:
        kind = message[0] if message else None
        if kind == "start":
            total[0] = max(int(message[1]), 1)
            feedback.setProgress(0)
        elif kind == "update":
            feedback.setProgress(int(100 * int(message[1]) / total[0]))
        elif kind == "finished":
            feedback.setProgress(100)

    signal.connect(report)


def _check_output_names(
    project: Any,
    configuration: RouteChoiceConfiguration,
    routes_folder: Path,
) -> None:
    """Reject result names that already exist in the project."""
    names = []
    if configuration["job"] == "assign":
        names.append(configuration["output_name"] + "_uncompressed")
    if configuration["select_links"]:
        names.append(configuration["select_link_name"] + "_uncompressed")
    if len({name.lower() for name in names}) != len(names):
        raise RouteChoiceError("Assignment and select-link outputs require different names")
    with project.results_connection as connection:
        existing = {row[0].lower() for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for name in names:
        if name.lower() in existing:
            raise RouteChoiceError(f"Results table '{name}' already exists")
    if configuration["select_links"]:
        matrix_name = configuration["select_link_name"]
        if project.matrices.check_exists(matrix_name) or (Path(project.matrices.fldr) / f"{matrix_name}.omx").exists():
            raise RouteChoiceError(f"Matrix '{matrix_name}' already exists")
    if configuration["sub_area"]:
        path = routes_folder / f"{configuration['output_name']}.parquet"
        if path.exists():
            raise RouteChoiceError(f"Sub-area output '{path.name}' already exists")


def _check_canceled(feedback: QgsProcessingFeedback | None) -> None:
    if feedback is not None and feedback.isCanceled():
        raise RouteChoiceError("Route-choice operation canceled")


def _info(feedback: QgsProcessingFeedback | None, message: str) -> None:
    if feedback is not None:
        feedback.pushInfo(message)


class RouteChoice(ProjectAlgorithm):
    """Build route-choice sets or assign demand for an AequilibraE project.

    The algorithm forms link utility as the sum of each coefficient multiplied by its
    network field. It uses that utility to generate paths for the selected mode.
    The selected demand cores determine which origin-destination demand the algorithm uses.

    Choose ``assign`` to save link-load results. Choose ``build`` to save route sets without
    assignment. Both operations can save route sets, omit links, and run select-link analysis.
    Sub-area analysis needs a polygon layer. It also writes external demand to a Parquet file.

    Processing inputs:
        PROJECT_FOLDER: AequilibraE project folder.
        MODE: Network mode ID.
        UTILITY_FIELDS: Rows of numeric coefficient and network field.
        ALGORITHM: ``bfsle`` or ``lp``.
        MAX_ROUTES and MAX_DEPTH: Stop limits. At least one must be greater than zero.
        PENALTY, CUTOFF, and BETA: Route penalty, probability cutoff, and PSL beta.
        BLOCK_CENTROID_FLOWS: Prevent paths from passing through other centroids.
        MATRIX_NAME and MATRIX_CORES: Project demand matrix record and selected cores.
        JOB: ``assign`` or ``build``.
        RESULT_NAME: Name for assignment results and sub-area output.
        SAVE_CHOICE_SETS: Save route sets during assignment.
        EXCLUDED_LINKS: Optional comma-separated link IDs to omit.
        SELECT_LINKS: Rows with a query name and link set. Link sets use ``ID:AB``,
            ``ID:BA``, or ``ID:Both`` items. Repeated query names define alternatives.
        SELECT_LINK_NAME: Optional select-link table and matrix name.
        SUB_AREA and ZONES: Enable sub-area processing and define its polygons.

    Processing outputs:
        OUTPUT_RESULT_NAME: Link-load table name, or an empty string for ``build``.
        OUTPUT_ROUTES_FOLDER: Choice-set folder, or an empty string when not saved.
        OUTPUT_SUB_AREA_MATRIX: Parquet path, or an empty string when not used.
        OUTPUT_SELECT_LINK_FLOWS: Select-link table name, or an empty string when not used.
        OUTPUT_SELECT_LINK_MATRIX: Select-link OMX path, or an empty string when not used.

    The algorithm rejects existing result and matrix names. It does not replace them.
    """

    MODE = "MODE"
    UTILITY_FIELDS = "UTILITY_FIELDS"
    ALGORITHM = "ALGORITHM"
    MAX_ROUTES = "MAX_ROUTES"
    MAX_DEPTH = "MAX_DEPTH"
    PENALTY = "PENALTY"
    CUTOFF = "CUTOFF"
    BETA = "BETA"
    BLOCK_CENTROID_FLOWS = "BLOCK_CENTROID_FLOWS"
    MATRIX_NAME = "MATRIX_NAME"
    MATRIX_CORES = "MATRIX_CORES"
    JOB = "JOB"
    RESULT_NAME = "RESULT_NAME"
    SAVE_CHOICE_SETS = "SAVE_CHOICE_SETS"
    EXCLUDED_LINKS = "EXCLUDED_LINKS"
    SELECT_LINKS = "SELECT_LINKS"
    SELECT_LINK_NAME = "SELECT_LINK_NAME"
    SUB_AREA = "SUB_AREA"
    ZONES = "ZONES"
    OUTPUT_RESULT_NAME = "OUTPUT_RESULT_NAME"
    OUTPUT_ROUTES_FOLDER = "OUTPUT_ROUTES_FOLDER"
    OUTPUT_SUB_AREA_MATRIX = "OUTPUT_SUB_AREA_MATRIX"
    OUTPUT_SELECT_LINK_FLOWS = "OUTPUT_SELECT_LINK_FLOWS"
    OUTPUT_SELECT_LINK_MATRIX = "OUTPUT_SELECT_LINK_MATRIX"
    project: Any | None = None
    zones: Any | None = None
    group_name = "Route choice"
    group_id = "route_choice"

    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        self.add_project_folder_parameter()
        self.addParameter(QgsProcessingParameterString(self.MODE, self.tr("Network mode")))
        self.addParameter(
            QgsProcessingParameterMatrix(
                self.UTILITY_FIELDS,
                self.tr("Utility terms"),
                headers=[self.tr("Coefficient"), self.tr("Network field")],
            )
        )
        self.addParameter(QgsProcessingParameterString(self.ALGORITHM, self.tr("Choice-set algorithm"), "bfsle"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_ROUTES,
                self.tr("Maximum routes"),
                type=Qgis.ProcessingNumberParameterType.Integer,
                minValue=0,
                defaultValue=3,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_DEPTH,
                self.tr("Maximum depth"),
                type=Qgis.ProcessingNumberParameterType.Integer,
                minValue=0,
                defaultValue=0,
            )
        )
        self.addParameter(QgsProcessingParameterNumber(self.PENALTY, self.tr("Link penalty"), defaultValue=1.0))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CUTOFF, self.tr("Probability cutoff"), defaultValue=0.0, minValue=0, maxValue=1
            )
        )
        self.addParameter(QgsProcessingParameterNumber(self.BETA, self.tr("PSL beta"), defaultValue=1.0))
        self.addParameter(
            QgsProcessingParameterBoolean(self.BLOCK_CENTROID_FLOWS, self.tr("Block flows through centroids"), False)
        )
        self.addParameter(QgsProcessingParameterString(self.MATRIX_NAME, self.tr("Demand matrix")))
        self.addParameter(
            QgsProcessingParameterString(self.MATRIX_CORES, self.tr("Demand matrix cores (comma-separated)"), "matrix")
        )
        self.addParameter(QgsProcessingParameterString(self.JOB, self.tr("Operation"), "assign"))
        self.addParameter(QgsProcessingParameterString(self.RESULT_NAME, self.tr("Results name"), "route_choice"))
        self.addParameter(QgsProcessingParameterBoolean(self.SAVE_CHOICE_SETS, self.tr("Save choice sets"), False))
        self.addParameter(
            QgsProcessingParameterString(
                self.EXCLUDED_LINKS, self.tr("Excluded link IDs (comma-separated)"), optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterMatrix(
                self.SELECT_LINKS,
                self.tr("Select-link queries"),
                headers=[self.tr("Name"), self.tr("Links (ID:direction, comma-separated)")],
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(self.SELECT_LINK_NAME, self.tr("Select-link output name"), optional=True)
        )
        self.addParameter(QgsProcessingParameterBoolean(self.SUB_AREA, self.tr("Use sub-area analysis"), False))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ZONES,
                self.tr("Sub-area polygons"),
                types=[Qgis.ProcessingSourceType.VectorPolygon],
                optional=True,
            )
        )
        self.addOutput(QgsProcessingOutputString(self.OUTPUT_RESULT_NAME, self.tr("Results table")))
        self.addOutput(QgsProcessingOutputFolder(self.OUTPUT_ROUTES_FOLDER, self.tr("Choice-set folder")))
        self.addOutput(QgsProcessingOutputFile(self.OUTPUT_SUB_AREA_MATRIX, self.tr("Sub-area demand table")))
        self.addOutput(QgsProcessingOutputString(self.OUTPUT_SELECT_LINK_FLOWS, self.tr("Select-link flows table")))
        self.addOutput(QgsProcessingOutputFile(self.OUTPUT_SELECT_LINK_MATRIX, self.tr("Select-link matrix")))

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, str]:
        try:
            configuration = self._configuration(parameters, context)
            project = self.project or self.project_folder(parameters, context)
            zones = getattr(self, "zones", None)
            if zones is None and configuration["sub_area"]:
                zones = self.parameterAsVectorLayer(parameters, self.ZONES, context)
            return _run_route_choice(project, configuration, zones, feedback)
        except RouteChoiceError as error:
            raise QgsProcessingException(self.tr(str(error))) from error
        except Exception as error:
            raise QgsProcessingException(self.tr(f"Route-choice operation failed: {error}")) from error

    def _configuration(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> RouteChoiceConfiguration:
        """Convert Processing values into validated route-choice settings."""
        mode = self.parameterAsString(parameters, self.MODE, context).strip()
        matrix_name = self.parameterAsString(parameters, self.MATRIX_NAME, context).strip()
        output_name = self.parameterAsString(parameters, self.RESULT_NAME, context).strip()
        job = self.parameterAsString(parameters, self.JOB, context).strip().lower()
        if not mode or not matrix_name or not output_name:
            raise RouteChoiceError("Mode, demand matrix and result name are required")
        if any(Path(name).name != name or "\\" in name for name in (output_name, matrix_name)):
            raise RouteChoiceError("Matrix and result names must not contain directory separators")
        if job not in {"assign", "build"}:
            raise RouteChoiceError("Operation must be 'assign' or 'build'")

        utility_values = self.parameterAsMatrix(parameters, self.UTILITY_FIELDS, context)
        if not utility_values or len(utility_values) % 2:
            raise RouteChoiceError("Utility terms require a coefficient and field for each row")
        utility_fields = []
        for index in range(0, len(utility_values), 2):
            try:
                coefficient = float(utility_values[index])
            except (TypeError, ValueError) as error:
                raise RouteChoiceError("Utility coefficients must be numeric") from error
            field = str(utility_values[index + 1] or "").strip()
            if not field:
                raise RouteChoiceError("Each utility term requires a network field")
            utility_fields.append((coefficient, field.lower()))

        algorithm = self.parameterAsString(parameters, self.ALGORITHM, context).strip().lower()
        if algorithm not in {"bfsle", "lp"}:
            raise RouteChoiceError("Choice-set algorithm must be 'bfsle' or 'lp'")
        max_routes = self.parameterAsInt(parameters, self.MAX_ROUTES, context)
        max_depth = self.parameterAsInt(parameters, self.MAX_DEPTH, context)
        if max_routes <= 0 and max_depth <= 0:
            raise RouteChoiceError("Maximum routes or maximum depth must be greater than zero")
        penalty = self.parameterAsDouble(parameters, self.PENALTY, context)
        select_links = _select_links(self.parameterAsMatrix(parameters, self.SELECT_LINKS, context))
        sub_area = self.parameterAsBool(parameters, self.SUB_AREA, context)
        select_link_name = (
            self.parameterAsString(parameters, self.SELECT_LINK_NAME, context).strip() or f"{output_name}_sl"
        )
        if Path(select_link_name).name != select_link_name or "\\" in select_link_name:
            raise RouteChoiceError("Select-link output names must not contain directory separators")
        return {
            "mode": mode,
            "utility_fields": utility_fields,
            "algorithm": algorithm,
            "kwargs": {
                "max_routes": max_routes,
                "max_depth": max_depth,
                "penalty": penalty,
                "cutoff_prob": self.parameterAsDouble(parameters, self.CUTOFF, context),
                "beta": self.parameterAsDouble(parameters, self.BETA, context),
                "store_results": not (
                    job == "assign" and not self.parameterAsBool(parameters, self.SAVE_CHOICE_SETS, context)
                ),
            },
            "block_centroid_flows": self.parameterAsBool(parameters, self.BLOCK_CENTROID_FLOWS, context),
            "matrix_name": matrix_name,
            "matrix_cores": [
                core.strip()
                for core in self.parameterAsString(parameters, self.MATRIX_CORES, context).split(",")
                if core.strip()
            ],
            "job": job,
            "output_name": output_name,
            "save_choice_sets": self.parameterAsBool(parameters, self.SAVE_CHOICE_SETS, context),
            "excluded_links": _parse_ids(self.parameterAsString(parameters, self.EXCLUDED_LINKS, context)),
            "select_links": select_links,
            "select_link_name": select_link_name,
            "sub_area": sub_area,
        }

    def name(self) -> str:
        return "route_choice"

    def displayName(self) -> str:
        return self.tr("Route choice")

    def shortHelpString(self) -> str:
        help_messages = [
            self.tr(
                "Builds route-choice sets or assigns demand for an AequilibraE project. "
                "Utility terms are coefficient and network-field pairs."
            ),
            self.tr("Choose 'assign' to save link-load results, or 'build' to save paths without assignment."),
            self.tr("Select at least one demand matrix core and one utility term."),
            self.tr("Set either a maximum route count or a maximum search depth above zero."),
            self.tr(
                "Optional inputs support blocked centroid flows, excluded links, select-link analysis, "
                "saved route sets, and sub-area analysis."
            ),
            self.tr("Sub-area analysis needs polygon features and writes an external-demand Parquet file."),
            self.tr(
                "Outputs identify the result table, choice-set folder, sub-area file, and optional "
                "select-link table and OMX matrix."
            ),
            self.tr("Existing result and matrix names are not replaced."),
        ]
        return "\n".join(help_messages)

    def createInstance(self) -> "RouteChoice":
        return type(self)()

    def tr(self, message: str) -> str:
        return trlt(type(self).__name__, message)


def _select_links(
    values: Sequence[Any] | None,
) -> dict[str, list[tuple[int, int] | list[tuple[int, int]]]]:
    """Parse query rows into named alternative sets of directed link IDs.

    Each row contains a query name and comma-separated ``ID:direction`` items.
    Repeated names add alternatives to the same query. A link without a direction
    uses ``Both``.
    """
    values = [value for value in values or [] if value is not None and str(value).strip() not in ("", "NULL", "None")]
    if not values:
        return {}
    directions = {"ab": 1, "ba": -1, "both": 0}
    selections = {}
    if len(values) % 2:
        raise RouteChoiceError("Select-link queries require a name and link set for each row")
    for index in range(0, len(values), 2):
        name, links = values[index : index + 2]
        name = str(name or "").strip()
        if not name:
            raise RouteChoiceError("Select-link queries require a name")
        link_set = []
        try:
            for item in str(links or "").split(","):
                if not item.strip():
                    continue
                link_id, separator, direction = item.partition(":")
                direction = direction.strip().lower() if separator else "both"
                if direction not in directions:
                    raise RouteChoiceError(f"Select-link query '{name}' has invalid direction '{direction}'")
                try:
                    link_id = int(link_id.strip())
                except ValueError as error:
                    raise RouteChoiceError(f"Select-link query '{name}' has invalid link IDs") from error
                link_set.append((link_id, directions[direction]))
        except RouteChoiceError:
            raise
        if not link_set:
            raise RouteChoiceError(f"Select-link query '{name}' requires at least one link ID")
        selections.setdefault(name, []).append(link_set)
    return selections


def _parse_ids(value: str | None) -> list[int]:
    """Parse comma-separated excluded-link IDs."""
    try:
        return [int(item.strip()) for item in str(value or "").split(",") if item.strip()]
    except ValueError as error:
        raise RouteChoiceError("Excluded link IDs must be integers separated by commas") from error

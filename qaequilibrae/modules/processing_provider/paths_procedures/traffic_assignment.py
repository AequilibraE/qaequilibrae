"""Traffic-assignment operation and its Processing adapter.

The operation takes native Processing parameters. Its reusable execution
function accepts an equivalent plain mapping, so the Traffic Assignment dialog
and exported Python runners do not duplicate AequilibraE setup.
"""

from collections.abc import Mapping
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingOutputString,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from ..project import open_project
from ..project_algorithm import ProjectAlgorithm


class TrafficAssignmentError(ValueError):
    """An invalid traffic-assignment configuration."""


def run_traffic_assignment(project_folder: str | Path, configuration: Mapping[str, Any], feedback=None) -> str:
    """Run and save an assignment described by ``configuration``.

    Returns the results-table name.  This deliberately has no QGIS dependency
    beyond the optional feedback object, so desktop callers can reuse it too.
    """
    assignment_options = _mapping(configuration, "assignment")
    result_name = _string(assignment_options, "result_name")
    traffic_class_options = configuration.get("traffic_classes")
    if not isinstance(traffic_class_options, list) or not traffic_class_options:
        raise TrafficAssignmentError("The assignment configuration requires at least one traffic class")

    _info(feedback, "Opening AequilibraE project")
    project_context = (
        nullcontext(project_folder) if hasattr(project_folder, "network") else open_project(project_folder)
    )
    with project_context as project:
        assignment, traffic_classes, has_skims, matrices = _build_assignment(
            project, traffic_class_options, assignment_options
        )
        try:
            _configure_select_links(traffic_classes, configuration.get("select_links"))
            _info(feedback, "Running traffic assignment")
            assignment.execute()
            _info(feedback, "Saving traffic-assignment results")
            _save_outputs(assignment, result_name, has_skims, configuration.get("select_links"))
        finally:
            for matrix in matrices:
                matrix.close()

    _info(feedback, f"Saved traffic-assignment results as {result_name}")
    return result_name


def _build_assignment(project, class_options, assignment_options):
    from aequilibrae.paths import TrafficAssignment as AequilibraeTrafficAssignment
    from aequilibrae.paths import TrafficClass

    traffic_classes = []
    matrices = []
    used_result_fields = set()
    for class_option in class_options:
        class_name, options = _traffic_class(class_option)
        if class_name.lower() in used_result_fields:
            raise TrafficAssignmentError(f"Traffic class name is repeated: {class_name}")
        used_result_fields.add(class_name.lower())

        matrix = _matrix(project, _string(options, "matrix_name"))
        matrices.append(matrix)
        matrix_cores = options.get("matrix_cores", [options.get("matrix_core")])
        if (
            not isinstance(matrix_cores, list)
            or not matrix_cores
            or not all(isinstance(core, str) for core in matrix_cores)
        ):
            raise TrafficAssignmentError(f"Traffic class '{class_name}' requires matrix_core or matrix_cores")
        matrix.computational_view(matrix_cores)
        matrix.view_names = [class_name if len(matrix_cores) == 1 else f"{class_name}_{core}" for core in matrix_cores]

        mode = _string(options, "network_mode")
        project.network.build_graphs(modes=[mode])
        graph = project.network.graphs[mode]
        graph.set_blocked_centroid_flows(bool(options.get("blocked_centroid_flows", False)))
        skims = options.get("skims", {})
        if not isinstance(skims, dict):
            raise TrafficAssignmentError(f"Traffic class '{class_name}' has invalid skims")
        if skims:
            graph.set_graph(_string(assignment_options, "time_field"))
            graph.set_skimming(list(skims))
            graph.set_blocked_centroid_flows(bool(options.get("blocked_centroid_flows", False)))

        traffic_class = TrafficClass(class_name, graph, matrix)
        traffic_class.set_pce(float(options.get("pce", 1.0)))
        if "fixed_cost" in options:
            traffic_class.set_vot(float(options.get("vot", 0)))
            traffic_class.set_fixed_cost(_string(options, "fixed_cost"))
        traffic_classes.append(traffic_class)

    assignment = AequilibraeTrafficAssignment()
    configure_traffic_assignment(assignment, traffic_classes, assignment_options)
    return assignment, traffic_classes, any(_traffic_class(item)[1].get("skims") for item in class_options), matrices


def _matrix(project, matrix_name):
    try:
        return project.matrices.get_matrix(matrix_name)
    except Exception as error:
        matrix_folder = Path(project.project_base_path) / "matrices"
        candidates = [matrix_folder / f"{matrix_name}.omx"]
        if matrix_name.endswith("_omx"):
            candidates.append(matrix_folder / f"{matrix_name.removesuffix('_omx')}.omx")
        matrix_path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if matrix_path is None:
            raise TrafficAssignmentError(f"Could not find matrix '{matrix_name}'") from error

        from aequilibrae.matrix import AequilibraeMatrix

        matrix = AequilibraeMatrix()
        matrix.load(matrix_path)
        return matrix


def configure_traffic_assignment(assignment, traffic_classes, assignment_options: Mapping[str, Any]):
    """Apply shared assignment settings to prepared AequilibraE traffic classes."""
    try:
        assignment.set_classes(traffic_classes)
        assignment.set_vdf(_string(assignment_options, "vdf"))
        assignment.set_vdf_parameters(
            {key: value for key, value in assignment_options.items() if key not in _ASSIGNMENT_KEYS}
        )
        assignment.set_capacity_field(_string(assignment_options, "capacity_field"))
        assignment.set_time_field(_string(assignment_options, "time_field"))
        assignment.set_algorithm(_string(assignment_options, "algorithm"))
        assignment.max_iter = int(assignment_options["max_iter"])
        assignment.rgap_target = float(assignment_options["rgap"])
    except (KeyError, TypeError, ValueError) as error:
        raise TrafficAssignmentError(f"Could not configure traffic assignment: {error}") from error


_ASSIGNMENT_KEYS = {
    "algorithm",
    "max_iter",
    "rgap",
    "capacity_field",
    "time_field",
    "result_name",
    "vdf",
}


def _configure_select_links(traffic_classes, options):
    if options is None:
        return
    options = _mapping({"select_links": options}, "select_links")
    selection = _mapping(options, "selection")
    for traffic_class in traffic_classes:
        traffic_class.set_select_links(selection)


def _save_outputs(assignment, result_name, has_skims, select_link_options):
    assignment.save_results(result_name)
    if has_skims:
        assignment.save_skims(result_name, which_ones="all", format="omx")
    if select_link_options is None:
        return
    options = _mapping({"select_links": select_link_options}, "select_links")
    output_name = _string(options, "output_name")
    if options.get("save_matrix", False):
        assignment.save_select_link_matrices(output_name)
    if options.get("save_result", False):
        assignment.save_select_link_flows(output_name)


def _traffic_class(value):
    if not isinstance(value, dict) or len(value) != 1:
        raise TrafficAssignmentError("Each traffic class must be a mapping with one class name")
    name, options = next(iter(value.items()))
    if not isinstance(name, str) or not name.strip() or not isinstance(options, dict):
        raise TrafficAssignmentError("Each traffic class needs a name and options")
    return name, options


def _mapping(mapping, key):
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise TrafficAssignmentError(f"The assignment configuration requires '{key}'")
    return value


def _string(mapping, key):
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise TrafficAssignmentError(f"The assignment configuration requires '{key}'")
    return value


def _info(feedback, message):
    if feedback is not None:
        feedback.pushInfo(message)


class RunTrafficAssignment(ProjectAlgorithm):
    """Run an AequilibraE traffic assignment from QGIS Processing parameters."""

    TRAFFIC_CLASSES = "TRAFFIC_CLASSES"
    SELECT_LINKS = "SELECT_LINKS"
    ALGORITHM = "ALGORITHM"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    RELATIVE_GAP = "RELATIVE_GAP"
    VDF = "VDF"
    ALPHA = "ALPHA"
    BETA = "BETA"
    TAU = "TAU"
    LENGTH = "LENGTH"
    CAPACITY_FIELD = "CAPACITY_FIELD"
    TIME_FIELD = "TIME_FIELD"
    RESULT_NAME = "RESULT_NAME"
    OUTPUT_RESULT_NAME = "OUTPUT_RESULT_NAME"
    group_name = "Path computation"
    group_id = "path_computation"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(
            QgsProcessingParameterMatrix(
                self.TRAFFIC_CLASSES,
                self.tr("Traffic classes"),
                headers=[
                    self.tr("Name"),
                    self.tr("Matrix"),
                    self.tr("Cores (comma-separated)"),
                    self.tr("Mode"),
                    self.tr("PCE"),
                    self.tr("Block centroid flows"),
                    self.tr("Fixed-cost field"),
                    self.tr("Value of time"),
                    self.tr("Skims (comma-separated)"),
                ],
            )
        )
        self.addParameter(
            QgsProcessingParameterMatrix(
                self.SELECT_LINKS,
                self.tr("Select-link queries"),
                headers=[self.tr("Name"), self.tr("Link IDs (comma-separated)"), self.tr("Direction: AB, BA, Both")],
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterString(self.ALGORITHM, self.tr("Assignment algorithm"), "bfw"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_ITERATIONS,
                self.tr("Maximum iterations"),
                type=Qgis.ProcessingNumberParameterType.Integer,
                defaultValue=100,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RELATIVE_GAP,
                self.tr("Relative gap"),
                type=Qgis.ProcessingNumberParameterType.Double,
                defaultValue=0.001,
                minValue=0,
            )
        )
        self.addParameter(QgsProcessingParameterString(self.VDF, self.tr("Volume-delay function"), "bpr"))
        self.addParameter(QgsProcessingParameterNumber(self.ALPHA, self.tr("VDF alpha"), defaultValue=0.15))
        self.addParameter(QgsProcessingParameterNumber(self.BETA, self.tr("VDF beta"), defaultValue=4.0))
        self.addParameter(QgsProcessingParameterNumber(self.TAU, self.tr("Akcelik tau"), defaultValue=0.0))
        self.addParameter(
            QgsProcessingParameterString(self.LENGTH, self.tr("Akcelik length field or value"), optional=True)
        )
        self.addParameter(QgsProcessingParameterString(self.CAPACITY_FIELD, self.tr("Capacity field"), "capacity"))
        self.addParameter(
            QgsProcessingParameterString(self.TIME_FIELD, self.tr("Free-flow time field"), "free_flow_time")
        )
        self.addParameter(QgsProcessingParameterString(self.RESULT_NAME, self.tr("Results table name"), "assignment"))
        self.addOutput(QgsProcessingOutputString(self.OUTPUT_RESULT_NAME, self.tr("Results table name")))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            configuration = self._configuration(parameters, context)
            result_name = run_traffic_assignment(self.project_folder(parameters, context), configuration, feedback)
        except TrafficAssignmentError as error:
            raise QgsProcessingException(self.tr(str(error))) from error
        except Exception as error:
            raise QgsProcessingException(self.tr(f"Traffic assignment failed: {error}")) from error
        return {self.OUTPUT_RESULT_NAME: result_name}

    def name(self):
        return "traffic_assignment"

    def displayName(self):
        return self.tr("Traffic assignment")

    def shortHelpString(self):
        return self.tr(
            "Runs a traffic assignment. Add one row per class; matrices, cores, modes, PCE, costs, and skims are set there."
        )

    def createInstance(self):
        return type(self)()

    def _configuration(self, parameters, context):
        vdf = self.parameterAsString(parameters, self.VDF, context).lower()
        assignment = {
            "algorithm": self.parameterAsString(parameters, self.ALGORITHM, context),
            "max_iter": self.parameterAsInt(parameters, self.MAX_ITERATIONS, context),
            "rgap": self.parameterAsDouble(parameters, self.RELATIVE_GAP, context),
            "vdf": vdf,
            "capacity_field": self.parameterAsString(parameters, self.CAPACITY_FIELD, context),
            "time_field": self.parameterAsString(parameters, self.TIME_FIELD, context),
            "result_name": self.parameterAsString(parameters, self.RESULT_NAME, context),
        }
        assignment.update(self._vdf_parameters(vdf, parameters, context))
        configuration = {
            "traffic_classes": _traffic_classes(self.parameterAsMatrix(parameters, self.TRAFFIC_CLASSES, context)),
            "assignment": assignment,
        }
        select_link_values = (
            self.parameterAsMatrix(parameters, self.SELECT_LINKS, context) if parameters.get(self.SELECT_LINKS) else []
        )
        select_links = _select_links(select_link_values)
        if select_links:
            configuration["select_links"] = {"selection": select_links, "output_name": assignment["result_name"]}
        return configuration

    def _vdf_parameters(self, vdf, parameters, context):
        parameters_by_vdf = {
            "bpr": (self.ALPHA, self.BETA),
            "bpr2": (self.ALPHA, self.BETA),
            "conical": (self.ALPHA, self.BETA),
            "inrets": (self.ALPHA,),
            "akcelik": (self.ALPHA, self.TAU, self.LENGTH),
        }
        try:
            names = parameters_by_vdf[vdf]
        except KeyError as error:
            raise TrafficAssignmentError(f"Unknown volume-delay function '{vdf}'") from error
        values = {}
        for name in names:
            if name == self.LENGTH:
                value = self.parameterAsString(parameters, name, context)
                if not value:
                    raise TrafficAssignmentError("Akcelik requires a length field or value")
            else:
                value = self.parameterAsDouble(parameters, name, context)
            values[name.lower()] = value
        return values


def _traffic_classes(values):
    rows = _matrix_rows(values, 9, "traffic classes")
    traffic_classes = []
    for name, matrix_name, cores, mode, pce, blocked, fixed_cost, vot, skims in rows:
        options = {
            "matrix_name": _required(name, matrix_name, "matrix"),
            "matrix_cores": _comma_separated(cores, name, "matrix cores"),
            "network_mode": _required(name, mode, "mode"),
            "pce": _float(pce, name, "PCE"),
            "blocked_centroid_flows": _boolean(blocked, name, "block centroid flows"),
            "skims": {skim: [] for skim in _comma_separated(skims, name, "skims", required=False)},
        }
        if fixed_cost:
            options["fixed_cost"] = str(fixed_cost)
            options["vot"] = _float(vot, name, "value of time")
        traffic_classes.append({str(name): options})
    if not traffic_classes:
        raise TrafficAssignmentError("At least one traffic class is required")
    return traffic_classes


def _select_links(values):
    if not any(value is not None and str(value).strip() for value in values):
        return {}
    selections = {}
    directions = {"ab": 1, "ba": -1, "both": 0}
    for name, link_ids, direction in _matrix_rows(values, 3, "select-link queries"):
        direction_key = str(direction).lower()
        if direction_key not in directions:
            raise TrafficAssignmentError(f"Select-link query '{name}' has invalid direction '{direction}'")
        try:
            selections[str(name)] = [(int(link_id), directions[direction_key]) for link_id in str(link_ids).split(",")]
        except ValueError as error:
            raise TrafficAssignmentError(f"Select-link query '{name}' has invalid link IDs") from error
    return selections


def _matrix_rows(values, columns, description):
    if len(values) % columns:
        raise TrafficAssignmentError(f"The {description} table has incomplete rows")
    return [values[index : index + columns] for index in range(0, len(values), columns)]


def _required(name, value, description):
    if not str(value).strip():
        raise TrafficAssignmentError(f"Traffic class '{name}' requires {description}")
    return str(value).strip()


def _comma_separated(value, name, description, required=True):
    values = [item.strip() for item in str(value).split(",") if item.strip()]
    if required and not values:
        raise TrafficAssignmentError(f"Traffic class '{name}' requires {description}")
    return values


def _float(value, name, description):
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise TrafficAssignmentError(f"Traffic class '{name}' has invalid {description}") from error


def _boolean(value, name, description):
    if str(value).lower() in {"true", "1", "yes"}:
        return True
    if str(value).lower() in {"false", "0", "no", ""}:
        return False
    raise TrafficAssignmentError(f"Traffic class '{name}' has invalid {description}")

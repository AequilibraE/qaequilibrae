"""Traffic-assignment Processing worker, shared by the dialog and project runners.

RunTrafficAssignment runs a static traffic assignment for one or more traffic classes,
saves the link-flow results to the AequilibraE project, and exposes the optional
select-link and skim outputs.
"""

import json
from collections.abc import Mapping
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from typing import Any

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputFile,
    QgsProcessingOutputFolder,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from ..project import borrow_project
from ..project_algorithm import ProjectAlgorithm


class TrafficAssignmentError(ValueError):
    """An invalid traffic-assignment configuration."""


def run_traffic_assignment(parameters, project=None, feedback=None):
    """Run the Processing worker from a dialog or an exported project runner."""
    algorithm = RunTrafficAssignment()
    algorithm.initAlgorithm()
    algorithm.project = project
    return algorithm.processAlgorithm(parameters, QgsProcessingContext(), feedback or QgsProcessingFeedback())


def _run_assignment(project_folder, configuration, feedback):
    assignment_options = _mapping(configuration, "assignment")
    result_name = _string(assignment_options, "result_name")
    traffic_class_options = configuration.get("traffic_classes")
    if not isinstance(traffic_class_options, list) or not traffic_class_options:
        raise TrafficAssignmentError("The assignment configuration requires at least one traffic class")

    _info(feedback, "Opening AequilibraE project")
    with borrow_project(project_folder) as project, ExitStack() as resources:
        _check_canceled(feedback)
        _check_output_names(project, configuration)
        assignment, traffic_classes = _build_assignment(
            project, traffic_class_options, assignment_options, resources, feedback
        )
        _configure_select_links(traffic_classes, configuration.get("select_links"))
        _check_canceled(feedback)
        _report_assignment_progress(assignment, feedback)
        _info(feedback, "Running traffic assignment")
        assignment.execute()
        _check_canceled(feedback)
        _info(feedback, "Saving traffic-assignment results")
        outputs = _save_outputs(assignment, configuration)

    _info(feedback, f"Saved traffic-assignment results as {result_name}")
    return outputs


def _build_assignment(project, class_options, assignment_options, resources, feedback):
    import numpy as np
    from aequilibrae.paths import TrafficAssignment as AequilibraeTrafficAssignment
    from aequilibrae.paths import TrafficClass

    traffic_classes = []
    used_result_fields = set()
    class_names = set()
    base_graphs = {}
    for class_option in class_options:
        class_name, options = _traffic_class(class_option)
        if class_name.lower() in class_names:
            raise TrafficAssignmentError(f"Traffic class name is repeated: {class_name}")
        class_names.add(class_name.lower())

        matrix = _matrix(project, _string(options, "matrix_name"))
        resources.callback(matrix.close)
        matrix_cores = options.get("matrix_cores", [options.get("matrix_core")])
        if (
            not isinstance(matrix_cores, list)
            or not matrix_cores
            or not all(isinstance(core, str) for core in matrix_cores)
        ):
            raise TrafficAssignmentError(f"Traffic class '{class_name}' requires matrix_core or matrix_cores")
        matrix.computational_view(matrix_cores)
        matrix.view_names = [class_name if len(matrix_cores) == 1 else f"{class_name}_{core}" for core in matrix_cores]
        # SQLite result columns are case insensitive, including generated multicore names.
        for field in matrix.view_names:
            if field.lower() in used_result_fields:
                raise TrafficAssignmentError(f"Repeated result field: {field}")
            used_result_fields.add(field.lower())
        nan_mask = np.isnan(matrix.matrix_view)
        if nan_mask.any():
            matrix.matrix_view[nan_mask] = 0.0
            _info(feedback, f"Replaced NaN demand with zero for traffic class '{class_name}'")

        mode = _string(options, "network_mode")
        if mode not in base_graphs:
            project.network.build_graphs(modes=[mode])
            base_graphs[mode] = deepcopy(project.network.graphs[mode])
        graph = deepcopy(base_graphs[mode])
        _fill_missing_mode_fields(graph, mode)
        if options.get("excluded_links"):
            graph.exclude_links(options["excluded_links"])
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

    assignment = AequilibraeTrafficAssignment(project)
    configure_traffic_assignment(assignment, traffic_classes, assignment_options)
    return assignment, traffic_classes


def _fill_missing_mode_fields(graph, mode: str) -> None:
    """Give links that do not carry ``mode`` usable values for their empty fields.

    ``build_graphs`` keeps links that do not support a mode, turning them into self-loops
    so the compressed graph culls them. They never carry flow, but they stay in the
    uncompressed graph, and the assignment rejects empty capacity, free-flow time and VDF
    parameters there. Filling those values keeps every mode's graph on the same set of
    links, which the assignment needs to sum flows across traffic classes.
    """
    network = graph.network
    if "modes" not in network.columns:
        return
    culled = ~network["modes"].astype("string").str.contains(mode, na=False, regex=False)
    if not culled.any():
        return
    numeric = network.select_dtypes(include="number").columns
    network.loc[culled, numeric] = network.loc[culled, numeric].fillna(1.0)
    graph.prepare_graph(graph.centroids)


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
        try:
            matrix.load(matrix_path)
        except Exception:
            matrix.close()
            raise
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
    selection = _mapping(options, "selection")
    for traffic_class in traffic_classes:
        traffic_class.set_select_links(selection)


def _save_outputs(assignment, configuration):
    result_name = configuration["assignment"]["result_name"]
    select_link_options = configuration.get("select_links")
    assignment.save_results(result_name)
    project = assignment.project
    outputs = {
        RunTrafficAssignment.OUTPUT_RESULT_NAME: result_name,
        RunTrafficAssignment.OUTPUT_DATABASE: str(project.project_base_path / "results_database.sqlite"),
        RunTrafficAssignment.OUTPUT_SKIMS: "[]",
        RunTrafficAssignment.OUTPUT_MATRIX_FOLDER: str(project.matrices.fldr),
        RunTrafficAssignment.OUTPUT_SELECT_LINK_MATRIX: "",
        RunTrafficAssignment.OUTPUT_SELECT_LINK_FLOWS: "",
    }
    outputs[RunTrafficAssignment.OUTPUT_SKIMS] = json.dumps(_save_skims(assignment, configuration))
    if select_link_options is None:
        return outputs
    output_name = _string(select_link_options, "output_name")
    if select_link_options.get("save_matrix", True):
        outputs[RunTrafficAssignment.OUTPUT_SELECT_LINK_MATRIX] = _save_select_link_matrices(assignment, output_name)
    if select_link_options.get("save_result", True):
        assignment.save_select_link_flows(output_name)
        outputs[RunTrafficAssignment.OUTPUT_SELECT_LINK_FLOWS] = output_name
    return outputs


def _save_skims(assignment, configuration):
    """Export only the final/blended cores requested for each traffic class."""
    class_options = dict(_traffic_class(item) for item in configuration["traffic_classes"])
    paths = []
    for cls in assignment.classes:
        choices = class_options[cls._id].get("skims", {})
        cores = [(field, kind) for field, kinds in choices.items() for kind in kinds]
        if not cores:
            continue
        name = f"{configuration['assignment']['result_name']}_{cls._id}"
        data = [
            (f"{field}_{kind}", (cls._aon_results.skims if kind == "final" else cls.results.skims).matrix[field])
            for field, kind in cores
        ]
        paths.append(_save_matrix(assignment, name, data, cls.graph.centroids, f"Assignment skims for class {cls._id}"))
    return paths


def _save_select_link_matrices(assignment, name):
    """Keep every demand core; the library exporter currently writes only core zero."""
    data = []
    for cls in assignment.classes:
        for query in cls.results.select_link_od.names:
            values = cls.results.select_link_od.get_matrix(query)
            for index, core in enumerate(cls.matrix.view_names):
                core_name = f"{query}_{cls._id}" if len(cls.matrix.view_names) == 1 else f"{query}_{core}"
                data.append((core_name, values[:, :, index]))
    return _save_matrix(assignment, name, data, assignment.classes[0].graph.centroids, "Select-link OD demand")


def _save_matrix(assignment, name, data, centroids, description):
    from aequilibrae.matrix import AequilibraeMatrix

    names = [core for core, _ in data]
    if len(set(names)) != len(names):
        raise TrafficAssignmentError("Matrix output core names are repeated")
    matrix = AequilibraeMatrix()
    try:
        matrix.create_empty(zones=len(centroids), matrix_names=names)
        assert matrix.index is not None and matrix.matrix is not None
        matrix.index[:] = centroids
        for core, values in data:
            matrix.matrix[core][:, :] = values[:, :]
        record = assignment.project.matrices.new_record(name, f"{name}.omx", matrix=matrix)
        record.procedure_id = assignment.procedure_id
        record.timestamp = assignment.procedure_date
        record.procedure = "Traffic Assignment"
        record.description = description
        record.save()
    finally:
        matrix.close()
    return str(Path(assignment.project.matrices.fldr) / f"{name}.omx")


def _report_assignment_progress(assignment, feedback):
    """Forward AequilibraE's per-iteration progress to the Processing feedback."""
    if feedback is None:
        return
    signal = getattr(getattr(assignment, "assignment", None), "signal", None)
    if signal is None or not hasattr(signal, "connect"):
        return

    total = [1]

    def report(message):
        kind = message[0] if message else None
        if kind == "start":
            total[0] = max(int(message[1]), 1)
            feedback.setProgress(0)
        elif kind == "update":
            feedback.setProgress(int(100 * int(message[1]) / total[0]))
        elif kind == "finished":
            feedback.setProgress(100)

    signal.connect(report)


def _check_canceled(feedback):
    if feedback is not None and feedback.isCanceled():
        raise TrafficAssignmentError("Traffic assignment canceled; results were not saved")


def _check_output_names(project, configuration):
    name = configuration["assignment"]["result_name"]
    tables = [name]
    matrices = [
        f"{name}_{_traffic_class(item)[0]}"
        for item in configuration["traffic_classes"]
        if _traffic_class(item)[1].get("skims")
    ]
    if selection := configuration.get("select_links"):
        output = _string(selection, "output_name")
        if selection.get("save_result", True):
            tables.append(output)
        if selection.get("save_matrix", True):
            matrices.append(output)
    if len(set(item.lower() for item in tables)) != len(tables):
        raise TrafficAssignmentError("Assignment and select-link flows require different result names")
    if len(set(item.lower() for item in matrices)) != len(matrices):
        raise TrafficAssignmentError("Skims and select-link matrices require different names")
    with project.results_connection as connection:
        existing = {row[0].lower() for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in tables:
        if table.lower() in existing:
            raise TrafficAssignmentError(f"Result table '{table}' already exists")
    for matrix in matrices:
        if Path(matrix).name != matrix or "\\" in matrix:
            raise TrafficAssignmentError("Matrix output names must not contain directory separators")
        if project.matrices.check_exists(matrix) or (Path(project.matrices.fldr) / f"{matrix}.omx").exists():
            raise TrafficAssignmentError(f"Matrix '{matrix}' already exists")


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
    """Run an AequilibraE traffic assignment from QGIS Processing parameters.

    Inputs: an AequilibraE project, one demand matrix per traffic class, network
    mode and assignment settings (algorithm, VDF, capacity and time fields, gap
    target), plus optional select-link queries and excluded links.

    Outputs: link-flow results saved to the project results database, optional
    skim OMX files per class, optional select-link OD and flow outputs, and an
    optional assigned-flows vector layer.
    """

    TRAFFIC_CLASSES = "TRAFFIC_CLASSES"
    SELECT_LINKS = "SELECT_LINKS"
    SELECT_LINK_NAME = "SELECT_LINK_NAME"
    SAVE_SELECT_LINK_MATRICES = "SAVE_SELECT_LINK_MATRICES"
    SAVE_SELECT_LINK_FLOWS = "SAVE_SELECT_LINK_FLOWS"
    EXCLUDED_LINKS = "EXCLUDED_LINKS"
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
    OUTPUT_FLOWS = "OUTPUT_FLOWS"
    OUTPUT_DATABASE = "OUTPUT_DATABASE"
    OUTPUT_MATRIX_FOLDER = "OUTPUT_MATRIX_FOLDER"
    OUTPUT_SKIMS = "OUTPUT_SKIMS"
    OUTPUT_SELECT_LINK_MATRIX = "OUTPUT_SELECT_LINK_MATRIX"
    OUTPUT_SELECT_LINK_FLOWS = "OUTPUT_SELECT_LINK_FLOWS"
    project = None
    group_name = "Traffic assignment"
    group_id = "traffic_assignment"

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
                    self.tr("Skims (field, field:final, or field:blended)"),
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
            QgsProcessingParameterMatrix(
                self.EXCLUDED_LINKS,
                self.tr("Excluded links by traffic class"),
                headers=[self.tr("Class"), self.tr("Link IDs (comma-separated)")],
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.SELECT_LINK_NAME,
                self.tr("Select-link output name (default: result name + _sl)"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SAVE_SELECT_LINK_MATRICES,
                self.tr("Save select-link OD matrices"),
                defaultValue=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SAVE_SELECT_LINK_FLOWS,
                self.tr("Save select-link flows"),
                defaultValue=True,
            )
        )
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
        self.addParameter(QgsProcessingParameterString(self.ALPHA, self.tr("VDF alpha field or value"), "0.15"))
        self.addParameter(QgsProcessingParameterString(self.BETA, self.tr("VDF beta field or value"), "4.0"))
        self.addParameter(QgsProcessingParameterString(self.TAU, self.tr("Akcelik tau field or value"), "0.0"))
        self.addParameter(QgsProcessingParameterString(self.LENGTH, self.tr("Akcelik length field or value")))
        self.addParameter(QgsProcessingParameterString(self.CAPACITY_FIELD, self.tr("Capacity field"), "capacity"))
        self.addParameter(
            QgsProcessingParameterString(self.TIME_FIELD, self.tr("Free-flow time field"), "free_flow_time")
        )
        self.addParameter(QgsProcessingParameterString(self.RESULT_NAME, self.tr("Results table name"), "assignment"))
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_FLOWS,
                self.tr("Assigned flows layer"),
                type=Qgis.ProcessingSourceType.VectorLine,
                optional=True,
            )
        )
        self.addOutput(QgsProcessingOutputString(self.OUTPUT_RESULT_NAME, self.tr("Results table name")))
        self.addOutput(QgsProcessingOutputFile(self.OUTPUT_DATABASE, self.tr("Results database")))
        self.addOutput(QgsProcessingOutputFolder(self.OUTPUT_MATRIX_FOLDER, self.tr("Matrix folder")))
        self.addOutput(QgsProcessingOutputString(self.OUTPUT_SKIMS, self.tr("Skim OMX paths (JSON array)")))
        self.addOutput(QgsProcessingOutputFile(self.OUTPUT_SELECT_LINK_MATRIX, self.tr("Select-link OMX")))
        self.addOutput(QgsProcessingOutputString(self.OUTPUT_SELECT_LINK_FLOWS, self.tr("Select-link flows table")))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            configuration = self._configuration(parameters, context)
            project_folder = self.project or self.project_folder(parameters, context)
            outputs = _run_assignment(project_folder, configuration, feedback)
            result_name = configuration["assignment"]["result_name"]
            outputs.update(self._flows_layer(project_folder, result_name, parameters, context, feedback))
            return outputs
        except TrafficAssignmentError as error:
            raise QgsProcessingException(self.tr(str(error))) from error
        except Exception as error:
            raise QgsProcessingException(self.tr(f"Traffic assignment failed: {error}")) from error

    def _flows_layer(self, project_folder, result_name, parameters, context, feedback):
        """Write the saved results, joined to the link geometry, to the feature sink."""
        if not parameters.get(self.OUTPUT_FLOWS):
            return {}
        from qaequilibrae.modules.matrix_procedures.load_result_table import load_result_table

        from ..geometry_io.common import add_dataframe_to_sink, fields_from_dataframe

        with borrow_project(project_folder) as project:
            links = project.network.links.data
            results = load_result_table(project, result_name)
            merged = links.merge(results, on="link_id", how="left")
            fields = fields_from_dataframe(merged)
            sink, destination = self.parameterAsSink(
                parameters,
                self.OUTPUT_FLOWS,
                context,
                fields,
                Qgis.WkbType.LineString,
                QgsCoordinateReferenceSystem("EPSG:4326"),
            )
            if sink is None:
                raise QgsProcessingException(self.tr("Could not create the assigned-flows layer"))
            add_dataframe_to_sink(merged, sink, fields, feedback)
        return {self.OUTPUT_FLOWS: destination}

    def name(self):
        return "traffic_assignment"

    def displayName(self):
        return self.tr("Traffic assignment")

    def shortHelpString(self):
        help_messages = [
            self.tr(
                "Runs a static traffic assignment for one or more traffic classes on an AequilibraE project "
                "and saves the link-flow results."
            ),
            self.tr("Inputs:"),
            self.tr("- AequilibraE project folder: the project whose network, modes and matrices are assigned."),
            self.tr(
                "- Traffic classes: one row per class, with columns Name, Matrix record, "
                "Cores (comma-separated), Mode, PCE, Block centroid flows (true/false), "
                "Fixed-cost field (optional), Value of time (optional) and Skims (optional)."
            ),
            self.tr(
                "- Assignment settings: algorithm, maximum iterations, relative gap, capacity field, "
                "free-flow time field, and the volume-delay function with its parameters "
                "(alpha, beta, tau and length, given as numbers or network field names)."
            ),
            self.tr("- Results table name: name of the flow table written to the results database."),
            self.tr(
                "- Select-link queries (optional): one row per query part, with columns Name, "
                "Link IDs (comma-separated) and Direction (AB, BA or Both). "
                "Rows sharing a name form one query; repeat the name to combine directions."
            ),
            self.tr(
                "- Excluded links (optional): one row per class, with columns Class and Link IDs (comma-separated)."
            ),
            self.tr("Outputs:"),
            self.tr(
                "- Results database and results table name: all link flows live in "
                "<project>/results_database.sqlite under the chosen table name."
            ),
            self.tr(
                "- Skims: one OMX file per class, named <result_name>_<class_name>.omx. "
                "A skim field produces final and blended cores by default; use "
                "field:final or field:blended to select one."
            ),
            self.tr(
                "- Select-link OD matrix and select-link flows table, when the corresponding "
                "switches are on. The matrix defaults to <result_name>_sl.omx and the table "
                "to <result_name>_sl."
            ),
            self.tr(
                "- Assigned-flows layer (optional): the project links joined with the results, "
                "ready to feed downstream algorithms."
            ),
            self.tr(
                "Output values also expose the matrix folder, and the skim paths as a JSON array. "
                "Cancellation stops before saving once the current computation finishes. "
                "Existing outputs are not overwritten."
            ),
        ]
        return "\n".join(help_messages)

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
        traffic_class_values = self.parameterAsMatrix(parameters, self.TRAFFIC_CLASSES, context)
        if not _matrix_has_rows(traffic_class_values):
            raise TrafficAssignmentError("At least one traffic class is required")
        configuration = {
            "traffic_classes": _traffic_classes(traffic_class_values),
            "assignment": assignment,
        }
        classes = {name: options for item in configuration["traffic_classes"] for name, options in item.items()}
        excluded_values = (
            self.parameterAsMatrix(parameters, self.EXCLUDED_LINKS, context)
            if parameters.get(self.EXCLUDED_LINKS)
            else []
        )
        excluded = excluded_values if _matrix_has_rows(excluded_values) else []
        for name, links in _matrix_rows(excluded, 2, "excluded links"):
            if name not in classes:
                raise TrafficAssignmentError(f"Unknown traffic class '{name}' in excluded links")
            classes[name]["excluded_links"] = [int(link) for link in str(links).split(",") if link.strip()]
        select_link_values = (
            self.parameterAsMatrix(parameters, self.SELECT_LINKS, context) if parameters.get(self.SELECT_LINKS) else []
        )
        select_links = _select_links(select_link_values)
        if select_links:
            configuration["select_links"] = {
                "selection": select_links,
                "output_name": self.parameterAsString(parameters, self.SELECT_LINK_NAME, context)
                or f"{assignment['result_name']}_sl",
                "save_matrix": self.parameterAsBool(parameters, self.SAVE_SELECT_LINK_MATRICES, context),
                "save_result": self.parameterAsBool(parameters, self.SAVE_SELECT_LINK_FLOWS, context),
            }
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
            value = self.parameterAsString(parameters, name, context).strip()
            if not value:
                raise TrafficAssignmentError(f"{vdf} requires {name.lower()} field or value")
            try:
                value = float(value)
            except ValueError:
                pass
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
            "skims": _skim_choices(skims, name),
        }
        if fixed_cost:
            options["fixed_cost"] = str(fixed_cost)
            options["vot"] = _float(vot, name, "value of time")
        traffic_classes.append({_required(name, name, "name"): options})
    if not traffic_classes:
        raise TrafficAssignmentError("At least one traffic class is required")
    return traffic_classes


def traffic_classes_from_project(project) -> list[dict]:
    """Suggest one traffic class per matrix core for a project.

    The project does not record which mode a matrix belongs to, so each core name is matched
    against the mode IDs and names. The match ignores case and lets a core name sit inside a
    mode name or the other way around (``motorcycle`` matches ``motorcycles``). When nothing
    matches, the project's first mode is used.
    """
    modes = project.network.modes.all_modes()
    modes_by_name = {mode.mode_name.lower(): mode_id for mode_id, mode in modes.items()}
    default_mode = next(iter(modes), "")
    used_names = set()
    traffic_classes = []
    for _, record in project.matrices.list().iterrows():
        if record.get("status"):
            continue
        matrix = project.matrices.get_matrix(record["name"])
        try:
            cores = list(matrix.names)
        finally:
            matrix.close()
        for core in cores:
            name = core
            if name in used_names:
                name = f"{Path(record['name']).stem}_{core}"
            used_names.add(name)
            mode_id = _match_mode(core, modes, modes_by_name, default_mode)
            mode = modes.get(mode_id) if mode_id else None
            traffic_classes.append(
                {
                    name: {
                        "matrix_name": record["name"],
                        "matrix_cores": [core],
                        "network_mode": mode_id,
                        "pce": getattr(mode, "pce", None) or 1.0,
                        "blocked_centroid_flows": False,
                        "skims": {},
                    }
                }
            )
    return traffic_classes


def _match_mode(core, modes, modes_by_name, default_mode):
    """Pick the mode whose ID or name best matches a matrix core name."""
    key = core.lower()
    if key in modes:
        return key
    if key in modes_by_name:
        return modes_by_name[key]
    for name, mode_id in modes_by_name.items():
        if key in name or name in key:
            return mode_id
    return default_mode


def _skim_choices(value, class_name):
    choices = {}
    for item in _comma_separated(value, class_name, "skims", required=False):
        field, separator, kind = item.partition(":")
        kinds = [kind.strip().lower()] if separator else ["final", "blended"]
        if not field.strip() or any(kind not in {"final", "blended"} for kind in kinds):
            raise TrafficAssignmentError(f"Traffic class '{class_name}' has invalid skim '{item}'")
        selected = choices.setdefault(field.strip(), [])
        selected.extend(kind for kind in kinds if kind not in selected)
    return choices


def _select_links(values):
    if not any(value is not None and str(value).strip() for value in values):
        return {}
    selections = {}
    directions = {"ab": 1, "ba": -1, "both": 0}
    for name, link_ids, direction in _matrix_rows(values, 3, "select-link queries"):
        direction_key = str(direction).strip().lower()
        if direction_key not in directions:
            raise TrafficAssignmentError(f"Select-link query '{name}' has invalid direction '{direction}'")
        query_name = str(name or "").strip()
        if not query_name:
            raise TrafficAssignmentError("Select-link queries require a name")
        try:
            selections.setdefault(query_name, []).extend(
                (int(link_id), directions[direction_key]) for link_id in str(link_ids).split(",")
            )
        except ValueError as error:
            raise TrafficAssignmentError(f"Select-link query '{name}' has invalid link IDs") from error
    return selections


def _matrix_has_rows(values):
    """Whether a Processing matrix parameter holds anything but its empty placeholder.

    QGIS gives an empty matrix back as an empty list, or as a single placeholder cell that
    can be ``None``, ``NULL`` or an empty string depending on the Qt version.
    """
    if values is None:
        return False
    return any(value is not None and str(value).strip() not in ("", "NULL", "None") for value in values)


def _matrix_rows(values, columns, description):
    if len(values) % columns:
        raise TrafficAssignmentError(f"The {description} table has incomplete rows")
    return [values[index : index + columns] for index in range(0, len(values), columns)]


def _required(name, value, description):
    if value is None or not str(value).strip():
        raise TrafficAssignmentError(f"Traffic class '{name}' requires {description}")
    return str(value).strip()


def _comma_separated(value, name, description, required=True):
    values = [item.strip() for item in str(value or "").split(",") if item.strip()]
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

"""Run transit assignment or create transit skim matrices."""

from qgis.core import (
    Qgis,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from qaequilibrae.modules.processing_provider.project import borrow_project
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm
from qaequilibrae.modules.transit_procedures.transit_assignment_runner import run_transit_assignment


class TransitAssignmentAlgorithm(ProjectAlgorithm):
    """Build transit networks, run assignment, and create transit skims."""

    algorithm_name = "transitAssignment"
    display_name = "Transit assignment and skimming"
    group_name = "Transit"
    group_id = "transit"

    ACTION = "ACTION"
    PERIOD_ID = "PERIOD_ID"
    USE_SAVED_GRAPH = "USE_SAVED_GRAPH"
    MATRIX_NAME = "MATRIX_NAME"
    MATRIX_CORE = "MATRIX_CORE"
    CLASS_NAME = "CLASS_NAME"
    RESULT_NAME = "RESULT_NAME"
    SKIM_FIELDS = "SKIM_FIELDS"

    def initAlgorithm(self, configuration: dict | None = None) -> None:
        self.add_project_folder_parameter()
        self.addParameter(
            QgsProcessingParameterEnum(
                self.ACTION,
                self.tr("Operation"),
                options=[self.tr("Create skim matrix"), self.tr("Assign demand")],
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PERIOD_ID,
                self.tr("Transit period ID"),
                type=Qgis.ProcessingNumberParameterType.Integer,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.USE_SAVED_GRAPH,
                self.tr("Use the saved transit graph"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.MATRIX_NAME,
                self.tr("Demand matrix (assignment) or skim output matrix (skimming)"),
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterString(self.MATRIX_CORE, self.tr("Demand matrix core"), optional=True))
        self.addParameter(
            QgsProcessingParameterString(self.CLASS_NAME, self.tr("Transit class name"), defaultValue="pt")
        )
        self.addParameter(
            QgsProcessingParameterString(self.RESULT_NAME, self.tr("Assignment result name"), optional=True)
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.SKIM_FIELDS,
                self.tr("Skim fields (comma-separated; create skim matrix only)"),
                defaultValue="trav_time",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "NETWORK_MODE", self.tr("Network mode for line geometry"), defaultValue="c", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                "CONNECTOR_METHOD",
                self.tr("Connector method"),
                options=[self.tr("Overlapping regions"), self.tr("Nearest neighbour")],
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                "LINE_METHOD",
                self.tr("Line geometry method"),
                options=[self.tr("Direct"), self.tr("Connector project match")],
                usesStaticStrings=True,
            )
        )
        for key, title, default in (
            ("OUTER_TRANSFERS", "Include outer stop transfers", True),
            ("INNER_TRANSFERS", "Include inner stop transfers", True),
            ("WALKING_EDGES", "Include walking edges", True),
            ("BLOCK_CENTROID_FLOWS", "Block centroid-to-centroid flows", False),
            ("SAVE_GRAPH", "Save the built transit graph", False),
        ):
            self.addParameter(QgsProcessingParameterBoolean(key, self.tr(title), defaultValue=default))

    def processAlgorithm(
        self,
        parameters: dict,
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict:
        folder = self.project_folder(parameters, context)
        if not folder:
            raise QgsProcessingException(self.tr("An AequilibraE project folder is required."))
        action_index = self.parameterAsEnum(parameters, self.ACTION, context)
        action = {0: "create", 1: "assign"}.get(action_index)
        if action is None:
            raise QgsProcessingException(self.tr("Select a valid transit operation."))

        matrix_name = self.parameterAsString(parameters, self.MATRIX_NAME, context).strip()
        matrix_core = self.parameterAsString(parameters, self.MATRIX_CORE, context).strip()
        class_name = self.parameterAsString(parameters, self.CLASS_NAME, context).strip()
        result_name = self.parameterAsString(parameters, self.RESULT_NAME, context).strip()
        skim_fields = [
            field.strip()
            for field in self.parameterAsString(parameters, self.SKIM_FIELDS, context).split(",")
            if field.strip()
        ]
        if not class_name:
            raise QgsProcessingException(self.tr("Transit class name must not be empty."))
        if action == "assign" and (not matrix_name or not matrix_core or not result_name):
            raise QgsProcessingException(self.tr("Assignment requires a demand matrix, core, and result name."))
        if action == "create" and (not matrix_name or not skim_fields):
            raise QgsProcessingException(
                self.tr("Skimming requires an output matrix name and at least one skim field.")
            )

        connector_methods = ("overlapping_regions", "nearest_neighbour")
        line_methods = ("direct", "connector project match")
        connector_index = self.parameterAsEnum(parameters, "CONNECTOR_METHOD", context)
        line_index = self.parameterAsEnum(parameters, "LINE_METHOD", context)
        if connector_index not in range(len(connector_methods)) or line_index not in range(len(line_methods)):
            raise QgsProcessingException(self.tr("Select valid graph-building methods."))

        configs = {
            "has_graph": self.parameterAsBool(parameters, self.USE_SAVED_GRAPH, context),
            "period_id": self.parameterAsInt(parameters, self.PERIOD_ID, context),
            "with_outer_stop_transfers": self.parameterAsBool(parameters, "OUTER_TRANSFERS", context),
            "with_inner_stop_transfers": self.parameterAsBool(parameters, "INNER_TRANSFERS", context),
            "with_walking_edges": self.parameterAsBool(parameters, "WALKING_EDGES", context),
            "blocking_centroid_flows": self.parameterAsBool(parameters, "BLOCK_CENTROID_FLOWS", context),
            "connector_method": connector_methods[connector_index],
            "line_method": line_methods[line_index],
            "mode_id": self.parameterAsString(parameters, "NETWORK_MODE", context).strip(),
            "save_graph": self.parameterAsBool(parameters, "SAVE_GRAPH", context),
            "mat_name": matrix_name,
            "matrix_name": matrix_name,
            "mat_core": [matrix_core],
            "class_name": class_name,
            "result_name": result_name,
            "skim_fields": skim_fields,
            "demand_matrix_core": "pt" if action == "create" else matrix_core,
            "time_field": "trav_time",
            "frequency_field": "freq",
        }
        try:
            with borrow_project(folder) as project:

                def report(step: int, maximum: int, message: str) -> None:
                    if feedback is None:
                        return
                    feedback.setProgress(step * 100 / maximum)
                    feedback.pushInfo(message)

                return run_transit_assignment(
                    project,
                    None,
                    configs,
                    action,
                    progress=report,
                    is_canceled=(lambda: feedback.isCanceled()) if feedback else None,
                )
        except InterruptedError:
            return {}
        except (KeyError, ValueError, RuntimeError) as error:
            raise QgsProcessingException(str(error)) from error

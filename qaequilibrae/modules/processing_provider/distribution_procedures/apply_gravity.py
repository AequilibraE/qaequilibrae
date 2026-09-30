"""Apply a synthetic gravity model as a Processing algorithm."""

from pathlib import Path

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from qaequilibrae.modules.processing_provider.project import open_project
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm

from .common import (
    GRAVITY_FUNCTIONS,
    add_trip_end_parameters,
    load_matrix_core,
    push_report,
    vectors_from_source,
)


class ApplyGravity(ProjectAlgorithm):
    """Produce a trip matrix by applying a synthetic gravity model to an impedance matrix."""

    algorithm_name = "apply_gravity_model"
    display_name = "Apply gravity model"
    group_name = "Distribution"
    group_id = "distribution"

    PROJECT_FOLDER = "PROJECT_FOLDER"
    IMPEDANCE_MATRIX_NAME = "IMPEDANCE_MATRIX_NAME"
    IMPEDANCE_MATRIX_CORE = "IMPEDANCE_MATRIX_CORE"
    VECTOR_SOURCE = "VECTOR_SOURCE"
    INDEX_FIELD = "INDEX_FIELD"
    ROW_FIELD = "ROW_FIELD"
    COLUMN_FIELD = "COLUMN_FIELD"
    FUNCTION = "FUNCTION"
    ALPHA = "ALPHA"
    BETA = "BETA"
    NAN_AS_ZERO = "NAN_AS_ZERO"
    OUTPUT_MATRIX = "OUTPUT_MATRIX"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter(self.PROJECT_FOLDER)
        self.addParameter(QgsProcessingParameterString(self.IMPEDANCE_MATRIX_NAME, self.tr("Impedance matrix name")))
        self.addParameter(QgsProcessingParameterString(self.IMPEDANCE_MATRIX_CORE, self.tr("Impedance matrix core")))
        add_trip_end_parameters(self)
        self.addParameter(
            QgsProcessingParameterEnum(
                self.FUNCTION,
                self.tr("Deterrence function"),
                options=GRAVITY_FUNCTIONS,
                defaultValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ALPHA,
                self.tr("Alpha (GAMMA and POWER)"),
                type=Qgis.ProcessingNumberParameterType.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BETA,
                self.tr("Beta (GAMMA and EXPO)"),
                type=Qgis.ProcessingNumberParameterType.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.NAN_AS_ZERO,
                self.tr("Treat NaN values as zero"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_MATRIX,
                self.tr("Output matrix"),
                fileFilter="OpenMatrix (*.omx)",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        from aequilibrae.distribution import GravityApplication

        project_folder = self.project_folder(parameters, context, self.PROJECT_FOLDER)
        matrix_name = self.parameterAsString(parameters, self.IMPEDANCE_MATRIX_NAME, context)
        core_name = self.parameterAsString(parameters, self.IMPEDANCE_MATRIX_CORE, context)
        source = self.parameterAsSource(parameters, self.VECTOR_SOURCE, context)
        if source is None:
            raise QgsProcessingException(self.tr("The trip-end vector layer could not be loaded"))

        row_field = self.parameterAsString(parameters, self.ROW_FIELD, context)
        column_field = self.parameterAsString(parameters, self.COLUMN_FIELD, context)
        output_path = self.parameterAsFileOutput(parameters, self.OUTPUT_MATRIX, context)
        vectors = vectors_from_source(
            source,
            self.parameterAsString(parameters, self.INDEX_FIELD, context),
            row_field,
            column_field,
        )
        model = self._build_model(parameters, context)
        nan_as_zero = self.parameterAsBool(parameters, self.NAN_AS_ZERO, context)

        feedback.pushInfo(self.tr("Loading the impedance matrix"))
        try:
            with (
                open_project(project_folder) as project,
                load_matrix_core(project, matrix_name, core_name) as impedance,
            ):
                feedback.pushInfo(self.tr("Applying the gravity model"))
                gravity = GravityApplication(
                    project=project,
                    model=model,
                    impedance=impedance,
                    vectors=vectors,
                    row_field=row_field,
                    column_field=column_field,
                    nan_as_zero=nan_as_zero,
                )
                gravity.apply()
                assert gravity.output is not None
                gravity.output.export(Path(output_path))
        except Exception as error:
            raise QgsProcessingException(self.tr(str(error))) from error

        push_report(feedback, gravity.report)
        return {self.OUTPUT_MATRIX: output_path}

    def _build_model(self, parameters, context):
        """Build and validate the synthetic gravity model from the parameters."""
        from aequilibrae.distribution import SyntheticGravityModel

        function = GRAVITY_FUNCTIONS[self.parameterAsEnum(parameters, self.FUNCTION, context)]
        model = SyntheticGravityModel()
        model.function = function

        if function in ("GAMMA", "POWER"):
            if parameters.get(self.ALPHA) in (None, ""):
                raise QgsProcessingException(
                    self.tr("The {function} function requires an alpha value").format(function=function)
                )
            model.alpha = self.parameterAsDouble(parameters, self.ALPHA, context)
        if function in ("GAMMA", "EXPO"):
            if parameters.get(self.BETA) in (None, ""):
                raise QgsProcessingException(
                    self.tr("The {function} function requires a beta value").format(function=function)
                )
            model.beta = self.parameterAsDouble(parameters, self.BETA, context)
        return model

    def shortHelpString(self):
        return self.tr(
            "Applies a synthetic gravity model to an impedance matrix and balances the result to "
            "the production and attraction totals. The vector index must contain the same zone "
            "IDs, in the same order, as the impedance matrix; the totals must balance. GAMMA "
            "requires alpha and beta, EXPO requires beta, and POWER requires alpha. The output "
            "is an OpenMatrix (*.omx) file."
        )

    def tags(self):
        return ["gravity", "distribution", "matrix", "synthetic"]

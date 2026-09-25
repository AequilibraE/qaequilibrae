"""Apply a synthetic gravity model as a Processing algorithm and shared operation."""

from typing import Any

import pandas as pd
from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.project import open_project

from .common import GRAVITY_FUNCTIONS, DistributionError, load_matrix_core, push_report, vectors_from_source


def apply_gravity_model(
    project: Any,
    model: Any,
    impedance: Any,
    vectors: pd.DataFrame,
    row_field: str,
    column_field: str,
    *,
    nan_as_zero: bool = False,
) -> tuple[Any, list[str]]:
    """Apply *model* to *impedance* and balance the result to *vectors*.

    Returns the produced matrix and the procedure report. Callers decide how to
    export the matrix and present :class:`DistributionError`.
    """
    from aequilibrae.distribution import GravityApplication

    try:
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
    except Exception as error:
        raise DistributionError(f"Gravity application failed: {error}") from error

    return gravity.output, gravity.report


class ApplyGravity(QgsProcessingAlgorithm):
    """Produce a trip matrix by applying a synthetic gravity model to an impedance matrix."""

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
        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECT_FOLDER,
                self.tr("AequilibraE project folder"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )
        self.addParameter(QgsProcessingParameterString(self.IMPEDANCE_MATRIX_NAME, self.tr("Impedance matrix name")))
        self.addParameter(QgsProcessingParameterString(self.IMPEDANCE_MATRIX_CORE, self.tr("Impedance matrix core")))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.VECTOR_SOURCE,
                self.tr("Trip-end vector layer"),
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.INDEX_FIELD,
                self.tr("Index field (zone ID)"),
                parentLayerParameterName=self.VECTOR_SOURCE,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.ROW_FIELD,
                self.tr("Production field"),
                parentLayerParameterName=self.VECTOR_SOURCE,
                type=Qgis.ProcessingFieldParameterDataType.Numeric,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.COLUMN_FIELD,
                self.tr("Attraction field"),
                parentLayerParameterName=self.VECTOR_SOURCE,
                type=Qgis.ProcessingFieldParameterDataType.Numeric,
            )
        )
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
        project_folder = self.parameterAsFile(parameters, self.PROJECT_FOLDER, context)
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
            with open_project(project_folder) as project:
                impedance = load_matrix_core(project, matrix_name, core_name)

                feedback.pushInfo(self.tr("Applying the gravity model"))
                output, report = apply_gravity_model(
                    project, model, impedance, vectors, row_field, column_field, nan_as_zero=nan_as_zero
                )
                output.export(output_path)
        except DistributionError as error:
            raise QgsProcessingException(self.tr(str(error))) from error

        push_report(feedback, report)
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

    def name(self):
        return "apply_gravity_model"

    def displayName(self):
        return self.tr("Apply gravity model")

    def group(self):
        return self.tr("Distribution")

    def groupId(self):
        return "distribution"

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

    def createInstance(self):
        return ApplyGravity()

    def tr(self, message):
        return trlt("ApplyGravity", message)

"""Iterative proportional fitting as a Processing algorithm and shared operation.

The :func:`fit_ipf` operation receives an AequilibraE matrix and trip-end vectors.
The :class:`IterativeProportionalFitting` adapter translates QGIS inputs and
outputs around it, so the operation stays independent from the desktop dialog.
"""

from typing import Any

import pandas as pd
from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.project import open_project

from .common import DistributionError, load_matrix_core, push_report, vectors_from_source


def fit_ipf(
    matrix: Any,
    vectors: pd.DataFrame,
    row_field: str,
    column_field: str,
    *,
    nan_as_zero: bool = False,
) -> tuple[Any, list[str]]:
    """Balance *matrix* so its row and column totals match *vectors*.

    Returns the fitted matrix and the procedure report. Callers decide how to
    export the matrix and present :class:`DistributionError`.
    """
    from aequilibrae.distribution import Ipf

    try:
        ipf = Ipf(
            matrix=matrix,
            vectors=vectors,
            row_field=row_field,
            column_field=column_field,
            nan_as_zero=nan_as_zero,
        )
        ipf.fit()
    except Exception as error:
        raise DistributionError(f"IPF failed: {error}") from error

    if ipf.error is not None:
        raise DistributionError(str(ipf.error))
    return ipf.output, ipf.report


class IterativeProportionalFitting(QgsProcessingAlgorithm):
    """Balance a seed matrix to a set of production and attraction totals."""

    PROJECT_FOLDER = "PROJECT_FOLDER"
    SEED_MATRIX_NAME = "SEED_MATRIX_NAME"
    SEED_MATRIX_CORE = "SEED_MATRIX_CORE"
    VECTOR_SOURCE = "VECTOR_SOURCE"
    INDEX_FIELD = "INDEX_FIELD"
    ROW_FIELD = "ROW_FIELD"
    COLUMN_FIELD = "COLUMN_FIELD"
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
        self.addParameter(QgsProcessingParameterString(self.SEED_MATRIX_NAME, self.tr("Seed matrix name")))
        self.addParameter(QgsProcessingParameterString(self.SEED_MATRIX_CORE, self.tr("Seed matrix core")))
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
        matrix_name = self.parameterAsString(parameters, self.SEED_MATRIX_NAME, context)
        core_name = self.parameterAsString(parameters, self.SEED_MATRIX_CORE, context)
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
        nan_as_zero = self.parameterAsBool(parameters, self.NAN_AS_ZERO, context)

        feedback.pushInfo(self.tr("Loading the seed matrix"))
        try:
            with open_project(project_folder) as project:
                seed_matrix = load_matrix_core(project, matrix_name, core_name)

                feedback.pushInfo(self.tr("Fitting the seed matrix"))
                output, report = fit_ipf(seed_matrix, vectors, row_field, column_field, nan_as_zero=nan_as_zero)
                output.export(output_path)
        except DistributionError as error:
            raise QgsProcessingException(self.tr(str(error))) from error

        push_report(feedback, report)
        return {self.OUTPUT_MATRIX: output_path}

    def name(self):
        return "iterative_proportional_fitting"

    def displayName(self):
        return self.tr("Iterative proportional fitting")

    def group(self):
        return self.tr("Distribution")

    def groupId(self):
        return "distribution"

    def shortHelpString(self):
        return self.tr(
            "Balances a seed matrix to production and attraction totals. The vector index must "
            "contain the same zone IDs, in the same order, as the matrix. Production and "
            "attraction totals must balance. The output is an OpenMatrix (*.omx) file. "
            "Also known as Fratar or Furness."
        )

    def tags(self):
        return ["ipf", "fratar", "furness", "distribution", "matrix"]

    def createInstance(self):
        return IterativeProportionalFitting()

    def tr(self, message):
        return trlt("IterativeProportionalFitting", message)

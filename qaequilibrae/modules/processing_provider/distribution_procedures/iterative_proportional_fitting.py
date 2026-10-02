"""Balance a seed matrix to trip-end vectors with iterative proportional fitting."""

from pathlib import Path

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from qaequilibrae.modules.processing_provider.project import open_project
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm

from .common import add_trip_end_parameters, load_matrix_core, push_report, vectors_from_source


class IterativeProportionalFitting(ProjectAlgorithm):
    """Balance a seed matrix to a set of production and attraction totals."""

    algorithm_name = "iterative_proportional_fitting"
    display_name = "Iterative proportional fitting"
    group_name = "Distribution"
    group_id = "distribution"

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
        self.add_project_folder_parameter(self.PROJECT_FOLDER)
        self.addParameter(QgsProcessingParameterString(self.SEED_MATRIX_NAME, self.tr("Seed matrix name")))
        self.addParameter(QgsProcessingParameterString(self.SEED_MATRIX_CORE, self.tr("Seed matrix core")))
        add_trip_end_parameters(self)
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
        from aequilibrae.distribution import Ipf

        project_folder = self.project_folder(parameters, context, self.PROJECT_FOLDER)
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
            with (
                open_project(project_folder) as project,
                load_matrix_core(project, matrix_name, core_name) as seed_matrix,
            ):
                feedback.pushInfo(self.tr("Fitting the seed matrix"))
                ipf = Ipf(
                    matrix=seed_matrix,
                    vectors=vectors,
                    row_field=row_field,
                    column_field=column_field,
                    nan_as_zero=nan_as_zero,
                )
                ipf.fit()
                if ipf.error is not None:
                    raise ValueError(str(ipf.error))
                ipf.output.export(Path(output_path))
        except Exception as error:
            raise QgsProcessingException(self.tr(str(error))) from error

        push_report(feedback, ipf.report)
        return {self.OUTPUT_MATRIX: output_path}

    def shortHelpString(self):
        return self.tr(
            "Balances a seed matrix to production and attraction totals. The vector index must "
            "contain the same zone IDs, in the same order, as the matrix. Production and "
            "attraction totals must balance. The output is an OpenMatrix (*.omx) file. "
            "Also known as Fratar or Furness."
        )

    def tags(self):
        return ["ipf", "fratar", "furness", "distribution", "matrix"]

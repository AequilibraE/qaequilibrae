"""Calibrate a synthetic gravity model as a Processing algorithm."""

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from qaequilibrae.modules.processing_provider.project import open_project
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm

from .common import CALIBRATION_FUNCTIONS, load_matrix_core, push_report


class CalibrateGravity(ProjectAlgorithm):
    """Fit a synthetic gravity model to an observed trip matrix."""

    algorithm_name = "calibrate_gravity_model"
    display_name = "Calibrate gravity model"
    group_name = "Distribution"
    group_id = "distribution"

    PROJECT_FOLDER = "PROJECT_FOLDER"
    OBSERVED_MATRIX_NAME = "OBSERVED_MATRIX_NAME"
    OBSERVED_MATRIX_CORE = "OBSERVED_MATRIX_CORE"
    IMPEDANCE_MATRIX_NAME = "IMPEDANCE_MATRIX_NAME"
    IMPEDANCE_MATRIX_CORE = "IMPEDANCE_MATRIX_CORE"
    FUNCTION = "FUNCTION"
    NAN_AS_ZERO = "NAN_AS_ZERO"
    OUTPUT_MODEL = "OUTPUT_MODEL"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter(self.PROJECT_FOLDER)
        self.addParameter(QgsProcessingParameterString(self.OBSERVED_MATRIX_NAME, self.tr("Observed matrix name")))
        self.addParameter(QgsProcessingParameterString(self.OBSERVED_MATRIX_CORE, self.tr("Observed matrix core")))
        self.addParameter(QgsProcessingParameterString(self.IMPEDANCE_MATRIX_NAME, self.tr("Impedance matrix name")))
        self.addParameter(QgsProcessingParameterString(self.IMPEDANCE_MATRIX_CORE, self.tr("Impedance matrix core")))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.FUNCTION,
                self.tr("Deterrence function"),
                options=CALIBRATION_FUNCTIONS,
                defaultValue=0,
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
                self.OUTPUT_MODEL,
                self.tr("Output model"),
                fileFilter="Model file (*.mod)",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        from aequilibrae.distribution import GravityCalibration

        project_folder = self.project_folder(parameters, context, self.PROJECT_FOLDER)
        observed_name = self.parameterAsString(parameters, self.OBSERVED_MATRIX_NAME, context)
        observed_core = self.parameterAsString(parameters, self.OBSERVED_MATRIX_CORE, context)
        impedance_name = self.parameterAsString(parameters, self.IMPEDANCE_MATRIX_NAME, context)
        impedance_core = self.parameterAsString(parameters, self.IMPEDANCE_MATRIX_CORE, context)
        function = CALIBRATION_FUNCTIONS[self.parameterAsEnum(parameters, self.FUNCTION, context)]
        nan_as_zero = self.parameterAsBool(parameters, self.NAN_AS_ZERO, context)
        output_path = self.parameterAsFileOutput(parameters, self.OUTPUT_MODEL, context)

        feedback.pushInfo(self.tr("Loading the observed and impedance matrices"))
        try:
            with (
                open_project(project_folder) as project,
                load_matrix_core(project, observed_name, observed_core) as observed,
                load_matrix_core(project, impedance_name, impedance_core) as impedance,
            ):
                feedback.pushInfo(self.tr("Calibrating the gravity model"))
                calibration = GravityCalibration(
                    project=project,
                    matrix=observed,
                    impedance=impedance,
                    function=function,
                    nan_as_zero=nan_as_zero,
                )
                calibration.calibrate()
                if calibration.error is not None:
                    raise ValueError(str(calibration.error))
                calibration.model.save(output_path)
        except Exception as error:
            raise QgsProcessingException(self.tr(str(error))) from error

        push_report(feedback, calibration.report)
        return {self.OUTPUT_MODEL: output_path}

    def shortHelpString(self):
        return self.tr(
            "Calibrates an EXPO or POWER model against an observed trip matrix and an impedance "
            "matrix. Both matrices must use matching zone IDs in the same order. The calibrated "
            "model is saved as a *.mod file."
        )

    def tags(self):
        return ["gravity", "calibration", "distribution", "model"]

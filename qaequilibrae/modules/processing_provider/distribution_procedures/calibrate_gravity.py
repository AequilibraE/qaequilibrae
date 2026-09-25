"""Calibrate a synthetic gravity model as a Processing algorithm and shared operation."""

from typing import Any

from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.project import open_project

from .common import CALIBRATION_FUNCTIONS, DistributionError, load_matrix_core, push_report


def calibrate_gravity_model(
    project: Any,
    matrix: Any,
    impedance: Any,
    function: str,
    *,
    nan_as_zero: bool = False,
) -> tuple[Any, list[str]]:
    """Calibrate a gravity model against an observed matrix and an impedance matrix.

    Returns the calibrated model and the procedure report. Callers decide how to
    save the model and present :class:`DistributionError`.
    """
    from aequilibrae.distribution import GravityCalibration

    try:
        calibration = GravityCalibration(
            project=project,
            matrix=matrix,
            impedance=impedance,
            function=function,
            nan_as_zero=nan_as_zero,
        )
        calibration.calibrate()
    except Exception as error:
        raise DistributionError(f"Gravity calibration failed: {error}") from error

    if calibration.error is not None:
        raise DistributionError(str(calibration.error))
    return calibration.model, calibration.report


class CalibrateGravity(QgsProcessingAlgorithm):
    """Fit a synthetic gravity model to an observed trip matrix."""

    PROJECT_FOLDER = "PROJECT_FOLDER"
    OBSERVED_MATRIX_NAME = "OBSERVED_MATRIX_NAME"
    OBSERVED_MATRIX_CORE = "OBSERVED_MATRIX_CORE"
    IMPEDANCE_MATRIX_NAME = "IMPEDANCE_MATRIX_NAME"
    IMPEDANCE_MATRIX_CORE = "IMPEDANCE_MATRIX_CORE"
    FUNCTION = "FUNCTION"
    NAN_AS_ZERO = "NAN_AS_ZERO"
    OUTPUT_MODEL = "OUTPUT_MODEL"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECT_FOLDER,
                self.tr("AequilibraE project folder"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )
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
        project_folder = self.parameterAsFile(parameters, self.PROJECT_FOLDER, context)
        observed_name = self.parameterAsString(parameters, self.OBSERVED_MATRIX_NAME, context)
        observed_core = self.parameterAsString(parameters, self.OBSERVED_MATRIX_CORE, context)
        impedance_name = self.parameterAsString(parameters, self.IMPEDANCE_MATRIX_NAME, context)
        impedance_core = self.parameterAsString(parameters, self.IMPEDANCE_MATRIX_CORE, context)
        function = CALIBRATION_FUNCTIONS[self.parameterAsEnum(parameters, self.FUNCTION, context)]
        nan_as_zero = self.parameterAsBool(parameters, self.NAN_AS_ZERO, context)
        output_path = self.parameterAsFileOutput(parameters, self.OUTPUT_MODEL, context)

        feedback.pushInfo(self.tr("Loading the observed and impedance matrices"))
        try:
            with open_project(project_folder) as project:
                observed = load_matrix_core(project, observed_name, observed_core)
                impedance = load_matrix_core(project, impedance_name, impedance_core)

                feedback.pushInfo(self.tr("Calibrating the gravity model"))
                model, report = calibrate_gravity_model(project, observed, impedance, function, nan_as_zero=nan_as_zero)
                model.save(output_path)
        except DistributionError as error:
            raise QgsProcessingException(self.tr(str(error))) from error

        push_report(feedback, report)
        return {self.OUTPUT_MODEL: output_path}

    def name(self):
        return "calibrate_gravity_model"

    def displayName(self):
        return self.tr("Calibrate gravity model")

    def group(self):
        return self.tr("Distribution")

    def groupId(self):
        return "distribution"

    def shortHelpString(self):
        return self.tr(
            "Calibrates an EXPO or POWER model against an observed trip matrix and an impedance "
            "matrix. Both matrices must use matching zone IDs in the same order. The calibrated "
            "model is saved as a *.mod file."
        )

    def tags(self):
        return ["gravity", "calibration", "distribution", "model"]

    def createInstance(self):
        return CalibrateGravity()

    def tr(self, message):
        return trlt("CalibrateGravity", message)

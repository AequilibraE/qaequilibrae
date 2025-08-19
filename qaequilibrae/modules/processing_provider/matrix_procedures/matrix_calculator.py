import importlib.util as iutil
import sys

import yaml
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)
from qgis.core import QgsProcessingException

from qaequilibrae.i18n.translate import trlt


class MatrixCalculator(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.operation_map = {
            "min(": "np.min(",
            "max(": "np.max(",
            "abs(": "np.absolute(",
            "ln(": "np.log(",
            "exp(": "np.exp(",
            "power(": "np.power(",
            "null_diag(": "np.null_diag(",
        }

        self.addParameter(
            QgsProcessingParameterFile(
                "conf_file",
                self.tr("Configuration file (*.yaml)"),
                behavior=QgsProcessingParameterFile.File,
            )
        )
        self.addParameter(QgsProcessingParameterString("procedure", self.tr("Expression"), multiLine=True))
        self.addParameter(
            QgsProcessingParameterString(
                "matrix_core", self.tr("Matrix core"), multiLine=False, defaultValue="matrix_core"
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination("file_path", self.tr("File path"), "AequilibraE Matrix (*.aem)")
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix

        if parameters["file_path"] is None:
            raise QgsProcessingException(self.tr("Plase use a valid file name."))

        feedback = QgsProcessingMultiStepFeedback(4, model_feedback)
        feedback.pushInfo(self.tr("Getting matrices from configuration file"))

        with open(parameters["conf_file"], "r") as f:
            params = yaml.safe_load(f)

        # Load matrices
        matrices = {}
        index = []
        for matrix in params:
            for name, values in matrix.items():
                mat = AequilibraeMatrix()
                mat.load(values["matrix_path"])
                matrices[name] = mat.get_matrix(values["matrix_core"])
                index[:] = mat.index[:]
                mat.close()

        expression = parameters["procedure"]

        # Replace the expression for numpy operations
        for key in self.operation_map.keys():
            if key in expression:
                expression = expression.replace(key, self.operation_map[key])

        # Replace the expression for matrices variables
        for key in matrices.keys():
            if key in expression:
                expression = expression.replace(key, f"matrices['{key}']")

        out = eval(expression)

        mat = AequilibraeMatrix()
        mat.create_empty(
            file_name=parameters["file_path"],
            zones=len(index),
            matrix_names=[parameters["matrix_core"]],
            memory_only=False,
        )
        mat.matrix[parameters["matrix_core"]][:, :] = out[:, :]
        mat.index[:] = index[:]
        mat.close()

        return {"Output": "Finished"}

    def name(self):
        return "matrixcalc"

    def displayName(self):
        return self.tr("Matrix calculator")

    def group(self):
        return self.tr("2. Data")

    def groupId(self):
        return "data"

    def shortHelpString(self):
        help_messages = [
            self.tr("Runs a matrix calculation based on a matrix configuration file (*.yaml) and an expression."),
            self.tr("Results are stored in an AequilibraE Matrix."),
            self.tr("Please notice that:"),
            self.tr(
                "- each key in the configuration file corresponds to the name of the matrix in the input expression;"
            ),
            self.tr("- expression must be written according to NumPy syntax."),
            self.tr("Examples of valid expressions and configuration are provided in the plugin documentation."),
        ]
        return "".join(help_messages)

    def createInstance(self):
        return MatrixCalculator()

    def tr(self, message):
        return trlt("MatrixCalculator", message)

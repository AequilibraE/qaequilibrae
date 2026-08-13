import importlib.util as iutil
import sys
from pathlib import Path

import numpy as np
import yaml
from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFileDestination, QgsProcessingParameterString, QgsProcessingException

from qaequilibrae.i18n.translate import trlt
from .matrix_expression import MatrixExpressionError, evaluate


class MatrixCalculator(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
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
            QgsProcessingParameterFileDestination("file_path", self.tr("File path"), "OpenMatrix (*.omx)")
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
                matrix_path = Path(values["matrix_path"])
                if matrix_path.suffix.upper() != ".OMX":
                    raise QgsProcessingException(
                        self.tr("Only OpenMatrix (*.omx) files are supported: {}").format(matrix_path)
                    )
                mat = AequilibraeMatrix()
                mat.load(matrix_path)
                matrices[name] = mat.get_matrix(values["matrix_core"])
                index[:] = mat.index[:]
                mat.close()

        try:
            out = evaluate(parameters["procedure"], matrices)
        except MatrixExpressionError as error:
            raise QgsProcessingException(self.tr("Invalid expression: {}").format(error)) from error

        # Expressions such as min(matrix) collapse to a single number, which cannot be written out
        expected = (len(index), len(index))
        if np.shape(out) != expected:
            got = self.tr("a single number") if np.shape(out) == () else f"{np.shape(out)}"
            raise QgsProcessingException(
                self.tr("The expression returned {}, but the result must be a {}x{} matrix").format(got, *expected)
            )

        mat = AequilibraeMatrix()
        mat.create_empty(zones=len(index), matrix_names=[parameters["matrix_core"]])
        mat.matrix[parameters["matrix_core"]][:, :] = out[:, :]
        mat.index[:] = index[:]
        mat.export(parameters["file_path"])
        mat.close()

        return {"Output": "Finished"}

    def name(self):
        return "matrixcalc"

    def displayName(self):
        return self.tr("Matrix calculator")

    def group(self):
        return self.tr("Data")

    def groupId(self):
        return "data"

    def shortHelpString(self):
        help_messages = [
            self.tr("Runs a matrix calculation based on a matrix configuration file (*.yaml) and an expression."),
            self.tr("Results are stored in an OpenMatrix (*.omx) file."),
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

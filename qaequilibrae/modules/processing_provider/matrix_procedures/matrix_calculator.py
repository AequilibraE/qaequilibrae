import importlib.util as iutil
import sys
from pathlib import Path

import numpy as np
import yaml
from qgis.core import Qgis, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFileDestination, QgsProcessingParameterString, QgsProcessingException

from qaequilibrae.modules.processing_provider.project_algorithm import ProcessingAlgorithm
from .matrix_expression import MatrixExpressionError, evaluate


class MatrixCalculator(ProcessingAlgorithm):
    algorithm_name = "matrixcalc"
    display_name = "Matrix calculator"
    group_name = "Data"
    group_id = "data"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "conf_file",
                self.tr("Configuration file (*.yaml)"),
                behavior=Qgis.ProcessingFileParameterBehavior.File,
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

    def processAlgorithm(self, parameters, context, feedback):
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix

        if parameters["file_path"] is None:
            raise QgsProcessingException(self.tr("Plase use a valid file name."))

        feedback = QgsProcessingMultiStepFeedback(4, feedback)
        feedback.pushInfo(self.tr("Getting matrices from configuration file"))

        with open(parameters["conf_file"], "r") as config_file:
            configuration = yaml.safe_load(config_file)

        matrices = {}
        index = None
        for matrix in configuration:
            for name, values in matrix.items():
                matrix_path = Path(values["matrix_path"])
                if matrix_path.suffix.upper() != ".OMX":
                    raise QgsProcessingException(
                        self.tr("Only OpenMatrix (*.omx) files are supported: {}").format(matrix_path)
                    )
                input_matrix = AequilibraeMatrix()
                input_matrix.load(matrix_path)
                matrices[name] = input_matrix.get_matrix(values["matrix_core"])
                if input_matrix.index is None:
                    raise QgsProcessingException(self.tr("Could not load matrix indices"))
                index = input_matrix.index.copy()
                input_matrix.close()

        if index is None:
            raise QgsProcessingException(self.tr("The configuration contains no matrices"))

        try:
            result = evaluate(parameters["procedure"], matrices)
        except MatrixExpressionError as error:
            raise QgsProcessingException(self.tr("Invalid expression: {}").format(error)) from error

        # Expressions such as min(matrix) collapse to a single number, which cannot be written out
        expected = (len(index), len(index))
        result_shape = np.shape(result)
        if result_shape != expected:
            got = self.tr("a single number") if result_shape == () else f"{result_shape}"
            raise QgsProcessingException(
                self.tr("The expression returned {}, but the result must be a {}x{} matrix").format(got, *expected)
            )

        output_matrix = AequilibraeMatrix()
        output_matrix.create_empty(zones=len(index), matrix_names=[parameters["matrix_core"]])
        if output_matrix.matrix is None or output_matrix.index is None:
            raise QgsProcessingException(self.tr("Could not create the output matrix"))
        output_matrix.matrix[parameters["matrix_core"]][:, :] = result[:, :]
        output_matrix.index[:] = index[:]
        output_matrix.export(Path(parameters["file_path"]))
        output_matrix.close()

        return {"Output": "Finished"}

    def shortHelpString(self):
        return self.tr(
            "Calculates an expression using matrices listed in a YAML configuration file. "
            "Use each YAML key as a matrix name in the expression. The result is saved as an "
            "OpenMatrix (*.omx) file. See the plugin documentation for examples."
        )

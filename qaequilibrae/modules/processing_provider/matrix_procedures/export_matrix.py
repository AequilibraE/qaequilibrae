import importlib.util as iutil
import sys
from os.path import join
from pathlib import Path

from qgis.core import Qgis, QgsProcessingException, QgsProcessingParameterEnum, QgsProcessingParameterFile

from qaequilibrae.modules.processing_provider.project_algorithm import ProcessingAlgorithm


class ExportMatrix(ProcessingAlgorithm):
    algorithm_name = "exportmatrices"
    display_name = "Export matrices"
    group_name = "Data"
    group_id = "data"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "matrix_path",
                self.tr("Matrix path"),
                behavior=Qgis.ProcessingFileParameterBehavior.File,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "file_path",
                self.tr("File path"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                "output_format",
                self.tr("File format"),
                options=[".csv", ".omx"],
                defaultValue=".csv",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix

        output_format = ("csv", "omx")[parameters["output_format"]]
        matrix_path = Path(parameters["matrix_path"])

        if matrix_path.suffix.lower() != ".omx":
            raise QgsProcessingException(self.tr("Only OpenMatrix (*.omx) files can be exported"))

        dst_path = join(parameters["file_path"], f"{matrix_path.stem}.{output_format}")

        mat = AequilibraeMatrix()

        if output_format == "omx":
            mat.create_from_omx(omx_path=parameters["matrix_path"], file_path=dst_path, memory_only=False)
        elif output_format == "csv":
            mat.create_from_omx(parameters["matrix_path"])
            mat.export(Path(dst_path))

        mat.close()

        return {"Output": dst_path}

    def shortHelpString(self):
        return self.tr("Exports an existing *.omx matrix file into *.csv or *.omx")

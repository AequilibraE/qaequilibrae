import importlib.util as iutil
import sys
from os.path import join

from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFile, QgsProcessingParameterEnum
from qgis.core import QgsMessageLog, Qgis

from qaequilibrae.i18n.translate import trlt


class ExportMatrix(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "matrix_path",
                self.tr("Matrix path"),
                behavior=QgsProcessingParameterFile.File,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "file_path",
                self.tr("File path"),
                behavior=QgsProcessingParameterFile.Folder,
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
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix

        file_format = ["csv", "omx"]
        format = file_format[parameters["output_format"]]
        file_name, ext = parameters["matrix_path"].split("/")[-1].split(".")
        dst_path = join(parameters["file_path"], f"{file_name}.{format}")

        kwargs = {"file_path": dst_path, "memory_only": False}
        mat = AequilibraeMatrix()

        if ext == "omx":
            if format == "omx":
                mat.create_from_omx(omx_path=parameters["matrix_path"], **kwargs)
            elif format in ["csv"]:
                mat.create_from_omx(parameters["matrix_path"])
                mat.export(dst_path)
        elif ext == "aem":
            mat.load(parameters["matrix_path"])
            mat.export(dst_path)
            QgsMessageLog.logMessage(
                self.tr("Support for AEM will be removed in a future version"), "Messages", Qgis.MessageLevel.Warning
            )

        mat.close()

        return {"Output": dst_path}

    def name(self):
        return "exportmatrices"

    def displayName(self):
        return self.tr("Export matrices")

    def group(self):
        return self.tr("Data")

    def groupId(self):
        return "data"

    def shortHelpString(self):
        return self.tr("Exports an existing matrix file into *.csv or *.omx")

    def createInstance(self):
        return ExportMatrix()

    def tr(self, message):
        return trlt("ExportMatrix", message)

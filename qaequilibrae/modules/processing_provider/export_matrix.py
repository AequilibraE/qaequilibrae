import importlib.util as iutil
import tempfile
import sys
from pathlib import Path
from os.path import join

from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFile, QgsProcessingParameterEnum

from qaequilibrae.i18n.translate import trlt


class ExportMatrix(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "srcFile",
                self.tr("Matrix"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="*.omx, *.aem",
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "destFolder",
                self.tr("Output folder"),
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                "outputformat",
                self.tr("File format"),
                options=[".csv", ".omx", ".aem"],
                defaultValue=".csv",
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):

        pathSource = parameters["srcFile"]
        fileformat = [".csv", ".omx", ".aem"]
        pathDest = join(parameters["destFolder"], Path(pathSource).stem + fileformat[parameters["outputformat"]])

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix

        if pathSource[-3:] == "omx":
            tmpmat = AequilibraeMatrix()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".aem").name
            tmpmat.create_from_omx(tmp, pathSource)
            tmpmat.export(tmp)
            pathSource = tmp
            tmpmat.close()
        mat = AequilibraeMatrix()
        mat.load(pathSource)
        mat.export(pathDest)
        mat.close()

        return {"Output": pathDest}

    def name(self):
        return self.tr("Export matrices")

    def displayName(self):
        return self.tr("Export matrices")

    def group(self):
        return self.tr("Data")

    def groupId(self):
        return self.tr("Data")

    def shortHelpString(self):
        return self.tr("Export an existing *.omx or *.aem matrix file into *.csv, *.aem or *.omx")

    def createInstance(self):
        return ExportMatrix()

    def tr(self, message):
        return trlt("ExportMatrix", message)

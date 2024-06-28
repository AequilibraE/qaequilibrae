import importlib.util as iutil
import sys
import numpy as np
import pandas as pd
from os.path import join
from scipy.sparse import coo_matrix

from qgis.core import QgsProcessingMultiStepFeedback, QgsProcessingParameterString, QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterField, QgsProcessingParameterMapLayer, QgsProcessingParameterFile
from qgis.core import QgsProcessingAlgorithm

from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.i18n.translate import trlt


class CreateMatrixFromLayer(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMapLayer("matrix_layer", self.tr("Matrix Layer")))
        self.addParameter(
            QgsProcessingParameterField(
                "origin",
                self.tr("Origin"),
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="matrix_layer",
                allowMultiple=False,
                defaultValue="origin",
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "destination",
                self.tr("Destination"),
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="matrix_layer",
                allowMultiple=False,
                defaultValue="destination",
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "value",
                self.tr("Value"),
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="matrix_layer",
                allowMultiple=False,
                defaultValue="value",
            )
        )
        self.addParameter(
            QgsProcessingParameterString("file_name", self.tr("File name"), multiLine=False, defaultValue="")
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "output_folder",
                self.tr("Output folder"),
                behavior=QgsProcessingParameterFile.Folder,
                fileFilter="All folders (*.*)",
                defaultValue=standard_path(),
            )
        )
        advparams = [
            QgsProcessingParameterString(
                "matrix_name", self.tr("Matrix name"), optional=True, multiLine=False, defaultValue=""
            ),
            QgsProcessingParameterString(
                "matrix_description",
                self.tr("Matrix description"),
                optional=True,
                multiLine=False,
                defaultValue="",
            ),
            QgsProcessingParameterString("matrix_core", self.tr("Matrix core"), multiLine=False, defaultValue="Value"),
        ]
        for param in advparams:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix

        origin = parameters["origin"]
        destination = parameters["destination"]
        value = parameters["value"]

        matrix_name = parameters["matrix_name"]
        matrix_description = parameters["matrix_description"]
        core_name = [parameters["matrix_core"]]

        output_folder = parameters["output_folder"]
        output_name = parameters["file_name"]
        file_name = join(output_folder, f"{output_name}.aem")

        # Import layer as a pandas df
        feedback.pushInfo(self.tr("Importing layer"))
        layer = self.parameterAsVectorLayer(parameters, "matrix_layer", context)
        cols = [origin, destination, value]
        datagen = ([f[col] for col in cols] for f in layer.getFeatures())
        matrix = pd.DataFrame.from_records(data=datagen, columns=cols)
        feedback.pushInfo("")
        feedback.setCurrentStep(1)

        # Getting all zones
        all_zones = np.unique(np.concatenate((matrices.Origine, matrices.Destination)))
        num_zones = all_zones.shape[0]
        idx = np.arange(num_zones)

        # Creates the indexing dataframes
        origs = pd.DataFrame({"from_index": all_zones, "from": idx})
        dests = pd.DataFrame({"to_index": all_zones, "to": idx})

        # adds the new index columns to the pandas dataframe
        matrix = matrix.merge(origs, left_on=origin, right_on="from_index", how="left")
        matrix = matrix.merge(dests, left_on=destination, right_on="to_index", how="left")

        agg_matrix = matrix.groupby(["from", "to"]).sum()

        # returns the indices
        agg_matrix.reset_index(inplace=True)

        # Creating the aequilibrae matrix file
        mat = AequilibraeMatrix()
        mat.name = matrix_name
        mat.description = matrix_description

        mat.create_empty(file_name=file_name, zones=num_zones, matrix_names=core_name, memory_only=False)
        mat.index[:] = all_zones[:]

        m = (
            coo_matrix((agg_matrix[value], (agg_matrix["from"], agg_matrix["to"])), shape=(num_zones, num_zones))
            .toarray()
            .astype(np.float64)
        )
        mat.matrix[core_name[0]][:, :] = m[:, :]
        feedback.pushInfo(self.tr("{}x{} matrix imported ").format(num_zones, num_zones))
        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        mat.save()
        mat.close()
        del agg_matrix, matrix, m

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)

        return {"Output": f"{mat.name}, {mat.description} ({file_name})"}

    def name(self):
        return self.tr("Create aem matrix file from layer")

    def displayName(self):
        return self.tr("Create aem matrix file from layer")

    def group(self):
        return ("02-"+self.tr("Data"))

    def groupId(self):
        return ("02-"+self.tr("Data"))

    def shortHelpString(self):
        return "\n".join([self.string_order(1), self.string_order(2), self.string_order(3), self.string_order(4)])

    def createInstance(self):
        return CreateMatrixFromLayer()

    def string_order(self, order):
        if order == 1:
            return self.tr("Save a layer as a *.aem file. Notice that:")
        elif order == 2:
            return self.tr("- the original matrix stored in the layer needs to be in list format")
        elif order == 3:
            return self.tr("- origin and destination fields need to be integers")
        elif order == 4:
            return self.tr("- value field can be either integer or real")

    def tr(self, message):
        return trlt("CreateMatrixFromLayer", message)

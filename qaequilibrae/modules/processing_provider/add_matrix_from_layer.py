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


class AddMatrixFromLayer(QgsProcessingAlgorithm):

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
            QgsProcessingParameterFile(
                "matrix_file",
                self.tr("Matrix file"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="*.aem",
                defaultValue=None,
            )
        
        self.addParameter(
            QgsProcessingParameterString(
                "matrix_core",
                self.tr("Matrix core"),
                multiLine=False, 
                defaultValue="Value"),
        ]

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix

        origin = parameters["origin"]
        destination = parameters["destination"]
        value = parameters["value"]

        core_name = parameters["matrix_core"]

        matrix_file = parameters["matrix_file"]

        # Import layer as a pandas df
        feedback.pushInfo(self.tr("Importing layer"))
        layer = self.parameterAsVectorLayer(parameters, "matrix_layer", context)
        cols = [origin, destination, value]
        datagen = ([f[col] for col in cols] for f in layer.getFeatures())
        matrix = pd.DataFrame.from_records(data=datagen, columns=cols)
        feedback.pushInfo("")
        feedback.setCurrentStep(1)

        # Getting all zones
        all_zones = np.array(sorted(list(set(list(matrix[origin].unique()) + list(matrix[destination].unique())))))
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
        mat.load(matrix_file)

        m = (
            coo_matrix((agg_matrix[value], (agg_matrix["from"], agg_matrix["to"])), shape=(num_zones, num_zones))
            .toarray()
            .astype(np.float64)
        )
        mat.matrix[core_name][:, :] = m[:, :]
        
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
        return self.tr("Add a matrix from a layer to an existing aem file")

    def displayName(self):
        return self.tr("Add a matrix from a layer to an existing aem file")

    def group(self):
        return self.tr("02-Data")

    def groupId(self):
        return self.tr("02-Data")

    def shortHelpString(self):
        return "\n".join([self.string_order(1), self.string_order(2), self.string_order(3), self.string_order(4)])

    def createInstance(self):
        return AddMatrixFromLayer()

    def string_order(self, order):
        if order == 1:
            return self.tr("Save a layer to an existing *.aem file. Notice that:")
        elif order == 2:
            return self.tr("- the original matrix stored in the layer needs to be in list format")
        elif order == 3:
            return self.tr("- origin and destination fields need to be integers")
        elif order == 4:
            return self.tr("- value field can be either integer or real")
        elif order == 5:
            return self.tr("- if matrix_core is already existing, then it will be updated and previous data will be lost")

    def tr(self, message):
        return trlt("AddMatrixFromLayer", message)

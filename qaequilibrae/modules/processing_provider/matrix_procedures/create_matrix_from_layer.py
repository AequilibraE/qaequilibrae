import importlib.util as iutil
import sys

import numpy as np
import pandas as pd
from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFileDestination
from qgis.core import QgsProcessingMultiStepFeedback, QgsProcessingParameterString, QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterField, QgsProcessingParameterMapLayer
from scipy.sparse import coo_matrix

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
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "destination",
                self.tr("Destination"),
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="matrix_layer",
                allowMultiple=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "value",
                self.tr("Value"),
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="matrix_layer",
                allowMultiple=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "matrix_core", self.tr("Matrix core"), multiLine=False, defaultValue="matrix_core"
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination("file_path", self.tr("File path"), "AequilibraE Matrix (*.aem)")
        )

        advparams = [
            QgsProcessingParameterString(
                "matrix_name",
                self.tr("Matrix name"),
                optional=True,
                multiLine=False,
            ),
            QgsProcessingParameterString(
                "matrix_description",
                self.tr("Matrix description"),
                optional=True,
                multiLine=False,
            ),
        ]
        for param in advparams:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix

        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)

        origin = parameters["origin"]
        destination = parameters["destination"]
        value = parameters["value"]
        list_cores = [parameters["matrix_core"]]
        path_to_file = parameters["file_path"]

        # Import layer as a pandas df
        feedback.pushInfo(self.tr("Importing layer"))
        layer = self.parameterAsVectorLayer(parameters, "matrix_layer", context)

        columns = [origin, destination, value]
        data = [feat.attributes() for feat in layer.getFeatures()]

        trip_df = pd.DataFrame(data=data, columns=columns)
        feedback.pushInfo("")
        feedback.setCurrentStep(1)

        # Borrowed from AequilibraE's "create_from_trip_list"
        zones_list = sorted(set(list(trip_df[origin].unique()) + list(trip_df[destination].unique())))
        zones_df = pd.DataFrame({"zone": zones_list, "idx": list(np.arange(len(zones_list)))})

        trip_df = trip_df.merge(
            zones_df.rename(columns={"zone": origin, "idx": origin + "_idx"}), on=origin, how="left"
        ).merge(zones_df.rename(columns={"zone": destination, "idx": destination + "_idx"}), on=destination, how="left")

        nb_of_zones = len(zones_list)
        feedback.pushInfo(self.tr("{}x{} matrix imported ").format(nb_of_zones, nb_of_zones))
        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        mat = AequilibraeMatrix()
        mat.create_empty(file_name=path_to_file, zones=nb_of_zones, matrix_names=list_cores, memory_only=False)

        m = (
            coo_matrix(
                (trip_df[value], (trip_df[origin + "_idx"], trip_df[destination + "_idx"])),
                shape=(nb_of_zones, nb_of_zones),
            )
            .toarray()
            .astype(np.float64)
        )

        mat.matrix[mat.names[0]][:, :] = m[:, :]
        mat.index[:] = zones_df["zone"][:]

        if "matrix_name" in parameters:
            mat.name = parameters["matrix_name"]
        if "matrix_description" in parameters:
            mat.description = parameters["matrix_description"]
        mat.close()

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)

        return {"Output": f"{mat.name}, {mat.description} ({path_to_file})"}

    def name(self):
        return "aemfromlayer"

    def displayName(self):
        return self.tr("Create AequilibraE matrix from layer")

    def group(self):
        return self.tr("2. Data")

    def groupId(self):
        return "data"

    def shortHelpString(self):
        help_messages = [
            self.tr("Saves layer as a new *.aem file. Note that:"),
            self.tr("- the original matrix stored in the layer needs to be in list format"),
            self.tr("- origin and destination fields need to be integers"),
            self.tr("- value field can be either integer or real"),
        ]
        return "\n".join(help_messages)

    def createInstance(self):
        return CreateMatrixFromLayer()

    def tr(self, message):
        return trlt("CreateMatrixFromLayer", message)

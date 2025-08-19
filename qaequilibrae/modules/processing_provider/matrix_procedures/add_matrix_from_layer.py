import importlib.util as iutil
import sys

import numpy as np
import pandas as pd
from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFileDestination
from qgis.core import QgsProcessingMultiStepFeedback, QgsProcessingParameterString
from qgis.core import QgsProcessingParameterField, QgsProcessingParameterMapLayer
from scipy.sparse import coo_matrix

from qaequilibrae.i18n.translate import trlt


class AddMatrixFromLayer(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFileDestination("file_path", self.tr("File path"), "Open Matrix (*.omx)")
        )
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
        self.addParameter(QgsProcessingParameterString("matrix_core", self.tr("Matrix core"), "matrix_core", False))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        import openmatrix as omx

        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)

        origin = parameters["origin"]
        destination = parameters["destination"]
        value = parameters["value"]

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

        m = (
            coo_matrix(
                (trip_df[value], (trip_df[origin + "_idx"], trip_df[destination + "_idx"])),
                shape=(nb_of_zones, nb_of_zones),
            )
            .toarray()
            .astype(np.float64)
        )

        mat = omx.open_file(parameters["file_path"], "a")
        mat[parameters["matrix_core"]] = m
        mat.close()

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)

        return {"Output": f"New core addedd to {parameters["file_path"]}"}

    def name(self):
        return "exportmatrixasomx"

    def displayName(self):
        return self.tr("Save matrix from layer in existing file")

    def group(self):
        return self.tr("2. Data")

    def groupId(self):
        return "data"

    def shortHelpString(self):
        help_messages = [
            self.tr("Saves a layer to an existing *.omx file. Notice that:"),
            self.tr("- the original matrix stored in the layer needs to be in list format"),
            self.tr("- origin and destination fields need to be integers"),
            self.tr("- value field can be either integer or real"),
            self.tr("- if matrix_core already exists, it will be updated and previous data will be lost"),
        ]
        return "\n".join(help_messages)

    def createInstance(self):
        return AddMatrixFromLayer()

    def tr(self, message):
        return trlt("AddMatrixFromLayer", message)

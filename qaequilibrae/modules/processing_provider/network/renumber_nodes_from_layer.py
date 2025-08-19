import importlib.util as iutil
import sys

import geopandas as gpd
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
from qgis.core import QgsProcessing, QgsProcessingMultiStepFeedback, QgsProcessingAlgorithm
from qgis.core import QgsProcessingParameterVectorLayer, QgsProcessingParameterField, QgsProcessingParameterFile
from shapely.wkt import loads, dumps

from qaequilibrae.i18n.translate import trlt


class RenumberNodesFromLayer(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "project_path",
                self.tr("Project path"),
                behavior=QgsProcessingParameterFile.Folder,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "nodes",
                self.tr("Centroids"),
                types=[QgsProcessing.TypeVectorPoint],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "node_id",
                self.tr("Node ID"),
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="nodes",
                allowMultiple=False,
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae import Project

        feedback.pushInfo(self.tr("Opening project"))

        project = Project()
        project.open(parameters["project_path"])

        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)

        feedback.pushInfo(self.tr("Importing nodes layer"))
        aeq_crs = QgsCoordinateReferenceSystem("EPSG:4326")

        # Import QGIS layer as a panda dataframe
        layer = self.parameterAsVectorLayer(parameters, "nodes", context)
        columns = [f.name() for f in layer.fields()]
        feature_list = []
        geometries = []
        for feat in layer.getFeatures():
            feature_list.append(feat.attributes())
            geom = feat.geometry()
            geom.transform(QgsCoordinateTransform(layer.crs(), aeq_crs, QgsProject.instance()))
            geometries.append(geom.asWkt().upper())
        df = gpd.GeoDataFrame(feature_list, columns=columns, geometry=gpd.GeoSeries.from_wkt(geometries), crs=4326)
        df["geometry"] = df["geometry"].apply(dumps, args=(True, 8))

        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        feedback.pushInfo(self.tr("Checking existing nodes"))

        # Import QGIS layer as a panda dataframe
        nodes = project.network.nodes
        nodes_data = gpd.GeoDataFrame(nodes.data, geometry=nodes.data["geometry"], crs=4326)
        nodes_data["geometry"] = nodes_data["geometry"].apply(dumps, args=(True, 8))

        feedback.pushInfo(" ")

        find = 0
        create = 0
        fail = 0
        for _, zone in df.iterrows():
            matching = nodes_data.loc[nodes_data["geometry"] == zone["geometry"]]
            if matching.shape[0] == 1:
                find += 1
                if zone[parameters["node_id"]] != matching["node_id"].iloc[0]:
                    update_node = nodes.get(matching["node_id"].iloc[0])
                    update_node.is_centroid = 1
                    update_node.renumber(zone[parameters["node_id"]])
                    update_node.save()
            elif matching.shape[0] == 0:
                create += 1
                new = nodes.new_centroid(zone[parameters["node_id"]])
                new.geometry = loads(zone["geometry"])
                new.save()
            elif matching.shape[0] > 1:
                fail += 1
                feedback.pushInfo(
                    self.tr("Multiple nodes found for zone {}. Unable to select node.").format(
                        zone[parameters["node_id"]]
                    )
                )
        feedback.pushInfo(self.tr("{} nodes found in input layer.").format(df.shape[0]))
        if find > 0:
            feedback.pushInfo(self.tr("{} centroids found an existing matching node").format(find))
        if create > 0:
            feedback.pushInfo(self.tr("{} new nodes added for unmatched centroids").format(create))
        if fail > 0:
            feedback.pushInfo(self.tr("{} centroids could not be processed").format(fail))
        feedback.pushInfo(" ")

        project.close()
        del df, nodes_data

        return {"Output": parameters["project_path"]}

    def name(self):
        return "renumbernodes"

    def displayName(self):
        return self.tr("Add/Renumber nodes from layer")

    def group(self):
        return self.tr("1. Model Building")

    def groupId(self):
        return "modelbuilding"

    def shortHelpString(self):
        help_messages = [
            self.tr("Adds or renumbers nodes in an AequilibraE project to match a layer of centroids."),
            self.tr("WARNING: you may have to change existing node_id (ex. using QGIS field calculator)"),
            self.tr("to ensure that changed node IDs (coming from Zone ID) are not already used."),
        ]
        return "\n".join(help_messages)

    def createInstance(self):
        return RenumberNodesFromLayer()

    def tr(self, message):
        return trlt("RenumberNodesFromLayer", message)

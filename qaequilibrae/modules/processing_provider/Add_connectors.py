import importlib.util as iutil
import sys
from os.path import join
import pandas as pd

from qgis.core import QgsProcessingMultiStepFeedback, QgsProcessing, QgsProcessingAlgorithm
from qgis.core import QgsProcessingParameterFile, QgsProcessingParameterNumber, QgsProcessingParameterString
from qgis.core import QgsFeature, QgsVectorLayer, QgsDataSourceUri

import processing

from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.i18n.translate import trlt

class AddConnectors(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterNumber(
                "num_connectors",
                self.tr("Connectors per centroid"),
                type=QgsProcessingParameterNumber.Integer,
                minValue=1,
                maxValue=10,
                defaultValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "mode", self.tr("Modes to connect (only one at a time)"), multiLine=False, defaultValue="c"
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "project_path",
                self.tr("Project path"),
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=standard_path(),
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)


        feedback.pushInfo(self.tr("Opening project"))
        project_path=parameters["project_path"]

        # Import nodes layer
        uri = QgsDataSourceUri()
        uri.setDatabase(join(project_path,'project_database.sqlite'))
        uri.setDataSource('', 'nodes', 'geometry')
        nodes_layer=QgsVectorLayer(uri.uri(), 'nodes_layer', 'spatialite')
        
        # Import links layer
        uri = QgsDataSourceUri()
        uri.setDatabase(join(project_path,'project_database.sqlite'))
        uri.setDataSource('', 'links', 'geometry')
        links_layer=QgsVectorLayer(uri.uri(), 'links_layer', 'spatialite')
        
        # Get current max link_id
        cols = ["link_id", "ogc_fid"]
        datagen = ([f[col] for col in cols] for f in links_layer.getFeatures())
        links_ids = pd.DataFrame.from_records(data=datagen, columns=cols)
        ogc_id = links_ids['ogc_fid'].max() + 1
        link_id = links_ids['link_id'].max() + 1

        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)
        
        feedback.pushInfo(self.tr('Extracting required nodes to process'))
        # Extract centroids to connect
        alg_params = {
            'EXPRESSION': '("is_centroid" = 1) AND ( not("modes" ILIKE \'%' + parameters["mode"] + '%\') OR "modes" IS NULL )',
            'INPUT': nodes_layer,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        ConnectFrom = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # Extract nodes to connect
        alg_params = {
            'EXPRESSION': '("is_centroid" = 0) AND ("modes" ILIKE \'%' + parameters["mode"] + '%\')',
            'INPUT': nodes_layer,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        ConnectTo = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)
        
        # Computing and adding connectors
        feedback.pushInfo(self.tr('Adding {} connectors when none exists for mode "{}"').format(parameters["num_connectors"], parameters["mode"]))
        
        alg_params = {
            'SOURCE': ConnectFrom['OUTPUT'],
            'DESTINATION': ConnectTo['OUTPUT'],
            'METHOD': 0,
            'DISTANCE': 10,
            'NEIGHBORS': parameters['num_connectors'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        Connectors = processing.run('native:shortestline', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        connectors_layer = context.takeResultLayer(Connectors['OUTPUT'])
        feature_list = []
        for f in connectors_layer.getFeatures():
            geom=f.geometry()
            nf=QgsFeature(links_layer.fields())
            nf.setGeometry(geom)
            nf['ogc_fid'] = int(ogc_id)
            nf['link_id'] = int(link_id)
            nf['a_node'] = 0
            nf['b_node'] = 0
            nf['direction'] = 0
            nf['capacity_ab'] = 99999
            nf['capacity_ba'] = 99999
            nf['link_type'] = 'centroid_connector'
            nf['name'] = 'centroid_connector zone '+ str(f["node_id"])
            nf['modes'] = f["modes_2"]
            feature_list.append(nf)
            ogc_id = ogc_id + 1
            link_id = link_id + 1
        links_layer.startEditing()
        links_layer.addFeatures(feature_list)
        links_layer.commitChanges()
        
        feedback.pushInfo(self.tr('{} connectors have been added').format(len(feature_list)))

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)
        del feature_list, nodes_layer, links_layer, connectors_layer

        return {"Output": parameters["project_path"]}

    def name(self):
        return self.tr("Add centroid connectors")

    def displayName(self):
        return self.tr("Add centroid connectors")

    def group(self):
        return ("01-"+self.tr("Model Building"))

    def groupId(self):
        return ("01-"+self.tr("Model Building"))

    def shortHelpString(self):
        return self.tr("Go through all the centroids and add connectors only if none exists for the chosen mode")

    def createInstance(self):
        return AddConnectors()

    def tr(self, message):
        return trlt("AddConnectors", message)

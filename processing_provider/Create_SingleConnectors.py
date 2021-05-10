__author__ = 'Arthur Evrard'

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
import processing

class CreateSingleConnectors(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('Nodeslayer', 'Nodes layer', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('nodeid', 'Node_id', type=QgsProcessingParameterField.Numeric, parentLayerParameterName='Nodeslayer', allowMultiple=False, defaultValue='node_id'))
        self.addParameter(QgsProcessingParameterVectorLayer('Centroidslayer', 'Centroids layer', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('centroidid', 'Centroid_id', type=QgsProcessingParameterField.Numeric, parentLayerParameterName='Centroidslayer', allowMultiple=False, defaultValue='node_id'))
        self.addParameter(QgsProcessingParameterNumber('StartconnectorIDat', 'Start connector ID at', type=QgsProcessingParameterNumber.Integer, defaultValue=1000))
        self.addParameter(QgsProcessingParameterString('Modes', 'Modes', multiLine=False, defaultValue='cbtw'))
        self.addParameter(QgsProcessingParameterFeatureSink('Connectors', 'connectors', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(9, model_feedback)
        results = {}
        outputs = {}

        # Distance au plus proche centre (ligne vers centre)
        alg_params = {
            'FIELD': parameters['nodeid'],
            'HUBS': parameters['Nodeslayer'],
            'INPUT': parameters['Centroidslayer'],
            'UNIT': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DistanceAuPlusProcheCentreLigneVersCentre'] = processing.run('qgis:distancetonearesthublinetohub', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}
        
        # link_id
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'link_id',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': QgsExpression(' \'\"fid\"+\'||'+str(parameters['StartconnectorIDat'])).evaluate(),
            'INPUT': outputs['DistanceAuPlusProcheCentreLigneVersCentre']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Link_id'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # A_node
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'a_node',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': parameters['centroidid'],
            'INPUT': outputs['Link_id']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['A_node'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # B_node
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'b_node',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': '\"HubName\"',
            'INPUT': outputs['A_node']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['B_node'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # direction
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'direction',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': '0',
            'INPUT': outputs['B_node']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Direction'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # distance
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'distance',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,
            'FORMULA': '\"HubDist\"',
            'INPUT': outputs['Direction']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Distance'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # modes
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'modes',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': '\''+parameters['Modes']+'\'',
            'INPUT': outputs['Distance']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Modes'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # link_type
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'link_type',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': '\'connector\'',
            'INPUT': outputs['Modes']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Link_type'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Supprimer champs
        alg_params = {
            'COLUMN': parameters['centroidid'] + ';HubName;HubDist',
            'INPUT': outputs['Link_type']['OUTPUT'],
            'OUTPUT': parameters['Connectors']
        }
        outputs['SupprimerChamps'] = processing.run('qgis:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Connectors'] = outputs['SupprimerChamps']['OUTPUT']
        return results

    def name(self):
        return 'Create single connectors'

    def displayName(self):
        return 'Create single connectors'

    def group(self):
        return 'Network'

    def groupId(self):
        return 'Network'
        
    def shortHelpString(self):
        return """
        From a layer of nodes and a layer of centroids, generate a polyline layer containing connectors. Connectors are created between each centroid and the nearest node and are pre-configured for AequilibraE as bidirectional.
        
        Parameters:
            Nodes_layer : the layer containing nodes from your network
            Node_id : node ID field 
            Centroids layer : the layer containing "centroids" of your zoning system
            Centroid_id : centroid ID field
            Start connector ID at : the number from which the connector IDs will start
            Modes : allowed modes
        """

    def createInstance(self):
        return CreateSingleConnectors()

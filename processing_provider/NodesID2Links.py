__author__ = 'Arthur Evrard'

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
import processing


class AddNodeInformationsToLinks(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('links', 'links', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('nodes', 'nodes', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('nodeid', 'node_id', type=QgsProcessingParameterField.Numeric, parentLayerParameterName='nodes', allowMultiple=False, defaultValue='node_id'))
        self.addParameter(QgsProcessingParameterFeatureSink('Calculated', 'calculated', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)
        results = {}
        outputs = {}

        # a_node
        alg_params = {
            'FIELD_LENGTH': QgsExpression('').evaluate(),
            'FIELD_NAME': 'a_node',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': 'aggregate(layer_property(\''+parameters['nodes']+'\',\'name\'),\'min\',\"'+parameters['nodeid']+'\", intersects(start_point(geometry(@parent)),$geometry))',
            'INPUT': parameters['links'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['A_node'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # b_node
        alg_params = {
            'FIELD_LENGTH': QgsExpression('').evaluate(),
            'FIELD_NAME': 'b_node',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': 'aggregate(layer_property(\''+parameters['nodes']+'\',\'name\'),\'min\',\"'+parameters['nodeid']+'\", intersects(end_point(geometry(@parent)),$geometry))',
            'INPUT': outputs['A_node']['OUTPUT'],
            'OUTPUT': parameters['Calculated']
        }
        outputs['B_node'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Calculated'] = outputs['B_node']['OUTPUT']
        return results

    def name(self):
        return 'NodesID2Links'

    def displayName(self):
        return 'Add node\'s IDs to links'

    def group(self):
        return 'Network'

    def groupId(self):
        return 'Network'
        
    def shortHelpString(self):
        return """
        From a layer of links and a layer of nodes, add to links ODs from starting and ending nodes. If "a_node" and/or "b_node" fields already exists, will update them.
        
        Parameters:
            Links : layer containing links from your network
            Nodes : layer containing nodes from your network
            Node_id : node ID field 
        """

    def createInstance(self):
        return AddNodeInformationsToLinks()

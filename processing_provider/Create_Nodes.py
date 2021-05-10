__author__ = 'Arthur Evrard'

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
import processing

class CreateNodes(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        # (links without connectors)
        self.addParameter(QgsProcessingParameterVectorLayer('Linkslayer', 'Links layer', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Nodes', 'nodes', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        results = {}
        outputs = {}

        # Extraire les extrem
        alg_params = {
            'INPUT': parameters['Linkslayer'],
            'VERTICES': '0,-1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtraireLesExtrem'] = processing.run('native:extractspecificvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Supprimer les géométries dupliquées
        alg_params = {
            'INPUT': outputs['ExtraireLesExtrem']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['SupprimerLesGomtriesDupliques'] = processing.run('native:deleteduplicategeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Delete
        alg_params = {
            'FIELDS_MAPPING': [],
            'INPUT': outputs['SupprimerLesGomtriesDupliques']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Delete'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Add ID
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'node_id',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': '$id',
            'INPUT': outputs['Delete']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddId'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Not centroid
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'is_centroid',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': '0',
            'INPUT': outputs['AddId']['OUTPUT'],
            'OUTPUT': parameters['Nodes']
        }
        outputs['NotCentroid'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Nodes'] = outputs['NotCentroid']['OUTPUT']
        return results

    def name(self):
        return 'Create nodes'

    def displayName(self):
        return 'Create nodes'

    def group(self):
        return 'Network'

    def groupId(self):
        return 'Network'
        
    def shortHelpString(self):
        return """
        From a link layer, generate a node layer pre-configurated for AequilibraE
        
        Parameters:
            Links layer : a polyline layer that contains links defining your network
        """

    def createInstance(self):
        return CreateNodes()

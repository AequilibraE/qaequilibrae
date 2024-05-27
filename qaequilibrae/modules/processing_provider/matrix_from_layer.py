from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
from qgis.core import QgsProcessingParameterVectorLayer, QgsProcessingParameterField, QgsProcessingParameterMapLayer, QgsProcessingParameterFile, QgsProcessingParameterString, QgsProcessingParameterDefinition
from .translatable_algo import TranslatableAlgorithm

import importlib.util as iutil
import os, sys
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix

class MatrixFromLayer(TranslatableAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMapLayer('matrix_layer', self.tr('Layer containing a matrix in list format')))
        self.addParameter(QgsProcessingParameterField('origin', self.tr('Origin field'), type=QgsProcessingParameterField.Numeric, parentLayerParameterName='matrix_layer', allowMultiple=False, defaultValue='origin'))
        self.addParameter(QgsProcessingParameterField('destination', self.tr('Destination field'), type=QgsProcessingParameterField.Numeric, parentLayerParameterName='matrix_layer', allowMultiple=False, defaultValue='destination'))
        self.addParameter(QgsProcessingParameterField('value', self.tr('Value field'), type=QgsProcessingParameterField.Numeric, parentLayerParameterName='matrix_layer', allowMultiple=False, defaultValue='value'))
        self.addParameter(QgsProcessingParameterString('FileName', self.tr('Name your output file'), multiLine=False, defaultValue=''))
        self.addParameter(QgsProcessingParameterFile('OutputFold', self.tr('Output folder'), behavior=QgsProcessingParameterFile.Folder, fileFilter='Tous les fichiers (*.*)', defaultValue='D:/'))
        advparams = [QgsProcessingParameterString('MatrixName', self.tr('Name of your matrix'), optional=True, multiLine=False, defaultValue=''),
                    QgsProcessingParameterString('MatrixDescription', self.tr('Something usefull to describe your matrix'), optional=True, multiLine=False, defaultValue=''),
                    QgsProcessingParameterString('CoreName', self.tr('Name for the core of your matrix'), multiLine=False, defaultValue='Value')
                    ]
        for param in advparams:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)
        
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr('AequilibraE library not found'))
        
        from aequilibrae.matrix import AequilibraeMatrix
        
        origin=parameters['origin']
        destination=parameters['destination']
        value=parameters['value']
        
        matrix_name=parameters['MatrixName']
        matrix_description=parameters['MatrixDescription']
        core_name=[parameters['CoreName']]
        
        output_folder=parameters['OutputFold']
        output_name=parameters['FileName']
        filename=os.path.join(output_folder,output_name+'.aem')
        
        # Import layer as a pandas df
        feedback.pushInfo(self.tr('Importing the layer from QGIS :'))
        layer = self.parameterAsVectorLayer(parameters, 'matrix_layer', context)
        cols=[origin,destination,value]
        datagen = ([f[col] for col in cols] for f in layer.getFeatures())
        matrix = pd.DataFrame.from_records(data=datagen, columns=cols)
        feedback.pushInfo(str(matrix.head(5)))
        feedback.pushInfo('...')
        feedback.pushInfo('')
        feedback.setCurrentStep(1)
        
        # Getting all zones
        all_zones = np.array(sorted(list(set( list(matrix[origin].unique()) + list(matrix[destination].unique())))))
        num_zones = all_zones.shape[0]
        idx = np.arange(num_zones)

        # Creates the indexing dataframes
        origs = pd.DataFrame({"from_index": all_zones, "from":idx})
        dests = pd.DataFrame({"to_index": all_zones, "to":idx})

        # adds the new index columns to the pandas dataframe
        matrix = matrix.merge(origs, left_on=origin, right_on='from_index', how='left')
        matrix = matrix.merge(dests, left_on=destination, right_on='to_index', how='left')

        agg_matrix = matrix.groupby(['from', 'to']).sum()

        # returns the indices
        agg_matrix.reset_index(inplace=True)

        # Creating the aequilibrae matrix file
        mat = AequilibraeMatrix()
        mat.name=matrix_name
        mat.description=matrix_description

        mat.create_empty(file_name = filename,
                         zones = num_zones,
                         matrix_names = core_name,
                         memory_only = False)
        mat.index[:] = all_zones[:]

        m = coo_matrix((agg_matrix[value], (agg_matrix['from'], agg_matrix['to'])), shape=(num_zones, num_zones)).toarray().astype(np.float64)
        mat.matrix[core_name[0]][:,:] = m[:,:]
        feedback.pushInfo(self.tr(f'Matrix imported as a {num_zones}x{num_zones} matrix'))
        feedback.pushInfo(' ')
        feedback.setCurrentStep(2)
        
        feedback.pushInfo(self.tr('A final sweep after the work...'))
        output=mat.name+", "+mat.description+" ("+filename+")"
        mat.save()
        mat.close()
        del matrix
        
        feedback.pushInfo(' ')
        feedback.setCurrentStep(3)
        
        return {'Output': output}

    def name(self):
        return self.tr('Create a .aem matrix file from a layer')

    def displayName(self):
        return self.tr('Create a .aem matrix file from a layer')

    def group(self):
        return self.tr('2_Matrix')

    def groupId(self):
        return self.tr('2_Matrix')

    def shortHelpString(self):
        return self.tr("""
        Save a layer as a .aem file :
        - the original matrix stored in the layer needs to be in list format
        - Origin and destination fields need to be integers
        - Value field can be integer or real
        """)

    def createInstance(self):
        return MatrixFromLayer(self.tr)
__author__ = 'Arthur Evrard'

import importlib.util as iutil
import os
import sys

import numpy as np
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFile

# Checks if we can display OMX
has_omx = iutil.find_spec("openmatrix") is not None

class omx2csv(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('omxFile', 'OMX file to convert (.omx)', behavior=QgsProcessingParameterFile.File, fileFilter='OMX (*.omx)', defaultValue=None))
        self.addParameter(QgsProcessingParameterFile('destFolder', 'Export matrices to', behavior=QgsProcessingParameterFile.Folder, fileFilter='Tous les fichiers (*.*)', defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        results = {}
        outputs = {}
        
        pathSource=parameters['omxFile']
        pathDest=parameters['destFolder']
        
        if not has_omx:
            sys.exit('Openmatrix library not found')
        import openmatrix as omx
        matrix=omx.open_file(pathSource)
        feedback = QgsProcessingMultiStepFeedback(len(matrix), model_feedback)

        feedback.setCurrentStep(0)
        feedback.pushInfo('')
        feedback.pushInfo('Dimensions of matrices to process: ')
        feedback.pushInfo(str(matrix.shape()))

        feedback.pushInfo('')
        feedback.pushInfo('Attributes in omx file: ')
        feedback.pushInfo(str(matrix.list_all_attributes()))
        Destination=np.array([list(matrix.mapping('main_index'))])
        Origin=np.transpose(np.array([[np.NaN]+list(matrix.mapping('main_index'))]))

        folder=os.path.join(pathDest,os.path.splitext(os.path.basename(pathSource))[0])
        if not os.path.exists(folder):
           os.makedirs(folder)

        for m in range(len(matrix)):
            n=matrix.list_matrices()[m]
            current=np.array(matrix[n])
            feedback.pushInfo('')
            feedback.pushInfo('Total stored in the "'+str(n)+'"matrix : ')
            feedback.pushInfo(str(int(round(current.sum(),0))))
            np.savetxt(f"{folder}/{n}.csv", np.c_[Origin, np.r_[Destination, current]], fmt='%.16g', delimiter=";")

            feedback.setCurrentStep(m)
            if feedback.isCanceled():
                return {}

        matrix.close()
        return results

    def name(self):
        return 'Convert OMX to CSV'

    def displayName(self):
        return 'Convert OMX to CSV'

    def group(self):
        return '2_Matrix'

    def groupId(self):
        return '2_Matrix'
        
    def shortHelpString(self):
        return """
        Export the matrices contained in an .omx file to a set of .csv files
        You need to install openmatrix library to use this function
        """

    def createInstance(self):
        return omx2csv()
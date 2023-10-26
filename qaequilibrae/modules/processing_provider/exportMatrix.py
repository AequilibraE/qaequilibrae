__author__ = 'Arthur Evrard'

import importlib.util as iutil
import os, tempfile
from pathlib import Path
import sys

from qaequilibrae.i18n.translator import tr
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum

class exportMatrix(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('srcFile', tr('Matrix file to convert (.omx or .aem)'), behavior=QgsProcessingParameterFile.File, fileFilter=tr('AequilibraE matrix formats (*.omx *.aem)'), defaultValue=None))
        self.addParameter(QgsProcessingParameterFile('destFolder', tr('Export matrices to'), behavior=QgsProcessingParameterFile.Folder, defaultValue=None))
        self.addParameter(QgsProcessingParameterEnum('outputformat', tr('Format to use for export'), options=['.csv','.omx','.aem'], defaultValue='.csv'))

    def processAlgorithm(self, parameters, context, model_feedback):
        results = {}
        outputs = {}
        
        pathSource=parameters['srcFile']
        fileformat=['.csv','.omx','.aem']     
        pathDest=os.path.join(parameters['destFolder'], Path(pathSource).stem+fileformat[parameters['outputformat']])
        
        # Checks if we have access to aequilibrae library
        has_aeq = iutil.find_spec("aequilibrae") is not None
        
        if not has_aeq:
            sys.exit(tr('AequilibraE library not found'))
        from aequilibrae.matrix import AequilibraeMatrix
        
        if pathSource[-3:]=='omx':
            tmpmat=AequilibraeMatrix()
            tmp=tempfile.NamedTemporaryFile(delete=False, suffix='.aem').name
            tmpmat.create_from_omx(tmp, pathSource)
            tmpmat.export(tmp)
            pathSource = tmp
            tmpmat.close()
        mat=AequilibraeMatrix()
        mat.load(pathSource)
        mat.export(pathDest)
        mat.close()
        
        return {'Output': pathDest}

    def name(self):
        return tr('Export omx or aem matrix to csv, aem or omx')

    def displayName(self):
        return tr('Export omx or aem matrix to csv, aem or omx')

    def group(self):
        return tr('2_Matrix')

    def groupId(self):
        return tr('2_Matrix')
        
    def shortHelpString(self):
        return tr("""
        Export an existing .omx or .aem matrix file into csv, aem or omx
        """)

    def createInstance(self):
        return exportMatrix()
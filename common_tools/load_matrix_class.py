"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loads matrix from file/layer
 Purpose:    Implements matrix loading

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    2017-02-26
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4.QtCore import *
import numpy as np
from scipy.sparse import coo_matrix
from worker_thread import WorkerThread
import uuid
import tempfile
import os
from auxiliary_functions import logger

class LoadMatrix(WorkerThread):
    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.layer = kwargs.get('layer')
        self.idx = kwargs.get('idx')
        self.max_zone = kwargs.get('max_zone', None)
        self.filler = kwargs.get('filler', 0)
        self.sparse = kwargs.get('sparse', False)
        self.mapped_array = kwargs.get('mapped_array', False)

        self.matrix = None
        self.error = None


    def doWork(self):
        layer = self.layer
        idx = self.idx
        max_zone = self.max_zone
        feat_count = layer.featureCount()
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (feat_count))

        error = None
        idx1 = idx[0]
        idx2 = idx[1]
        idx3 = idx[2]
        # We read all the vectors and put in a list of lists
        matrix = []
        P = 0
        for feat in layer.getFeatures():
            P += 1
            a = feat.attributes()[idx1]
            b = feat.attributes()[idx2]
            c = feat.attributes()[idx3]
            matrix.append([a, b, c])
            if P % 1000 == 0:
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(P)))
                self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),
                          ("Loading matrix: " + str(P) + "/" + str(feat_count)))

        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (0))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), ("Converting Matrix to a NumPy array"))
        matrix = np.array(matrix)  # transform the list of lists in NumPy array

        if max_zone != np.max(matrix[:, 0:2]) + 1 and max_zone is not None:
            error = 'Vectors and matrix do not have matching dimensions'  # Compute number of zones in the problem
        mat = 0
        if max_zone is None:
            max_zone = np.max(matrix[:, 0:2]) + 1
        if error is None:
            if self.sparse:
                mat = coo_matrix((matrix[:,2], (matrix[:,0], matrix[:,1])), shape=(max_zone, max_zone))
            else:
                if self.mapped_array:
                    mat = np.memmap(os.path.join(tempfile.gettempdir(),'aequilibrae_array_' + str(uuid.uuid4().hex) + '.mat'),
                                    dtype=np.float_,
                                    mode='w+',
                                    shape=(int(max_zone), int(max_zone)))
                else:
                    mat = np.zeros((int(max_zone), int(max_zone)))
                if self.filler != 0:
                    mat.fill(self.filler)

                P = 0
                for i in matrix:
                    mat[i[0].astype(int), i[1].astype(int)] = i[2]
                    P += 1
                    if P % 1000 == 0:
                        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(P)))
                        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),
                                  ("Converting matrix: " + str(P) + "/" + str(feat_count)))
        self.matrix = mat
        self.error = error
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(feat_count)))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), ("Matrix loading finalized"))
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), 'LOADED-MATRIX')
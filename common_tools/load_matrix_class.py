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
 Updated:    2017-06-10
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import os
import tempfile
import uuid
from scipy.sparse import coo_matrix

import numpy as np
from PyQt4.QtCore import *

from aequilibrae.matrix import AequilibraeMatrix
from worker_thread import WorkerThread


class LoadMatrix(WorkerThread):
    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.matrix_type = kwargs.get('type')
        self.numpy_file = kwargs.get('file_path')
        self.layer = kwargs.get('layer')
        self.idx = kwargs.get('idx')
        self.filler = kwargs.get('filler', 0)
        self.sparse = kwargs.get('sparse', False)

        self.matrix = None
        self.matrix_hash = None
        self.titles = None
        self.report = []

    def doWork(self):
        if self.matrix_type == 'layer':
            self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), "Loading from table")
            feat_count = self.layer.featureCount()
            self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (feat_count))

            # We read all the vectors and put in a list of lists
            matrix = []
            P = 0
            for feat in self.layer.getFeatures():
                P += 1
                a = feat.attributes()[self.idx[0]]
                b = feat.attributes()[self.idx[1]]
                c = feat.attributes()[self.idx[2]]
                matrix.append([a, b, c])
                if P % 1000 == 0:
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(P)))
                    self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),
                              ("Loading matrix: " + str(P) + "/" + str(feat_count)))

            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (0))
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), ("Converting to a NumPy array"))
            matrix1 = np.array(matrix)  # transform the list of lists in NumPy array

            # Bring it all to memory mapped
            self.matrix = np.memmap(os.path.join(tempfile.gettempdir(),'aequilibrae_temp_file_' + str(uuid.uuid4().hex) + '.mat'),
                               dtype=np.float64,
                               mode='w+',
                               shape=(int(matrix1.shape[0]), 3))
            self.matrix[:] = matrix1[:]
            del(matrix1)

        elif self.matrix_type == 'numpy':
            self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), "Loading from NumPY")
            try:
                mat= np.load(self.numpy_file)
                if len(mat.shape[:]) == 2:
                    mat = coo_matrix(mat)
                    cells = int(mat.row.shape[0])
                    self.matrix = np.memmap(os.path.join(tempfile.gettempdir(),'aequilibrae_temp_file_' + str(uuid.uuid4().hex) + '.mat'),
                                            dtype=np.float64,
                                            mode='w+',
                                            shape=(cells, 3))
                    self.matrix[:,0] = mat.row[:]
                    self.matrix[:,1] = mat.col[:]
                    self.matrix[:,2] = mat.data[:]
                    del(mat)
                else:
                    self.report.append('Numpy array needs to be 2 dimensional. Matrix provided has ' + str(len(mat.shape[:])))
            except:
                self.report.append('Could not load array')

        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), '')
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), 'LOADED-MATRIX')


class MatrixReblocking(WorkerThread):
    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.matrices = kwargs.get('matrices')
        self.sparse = kwargs.get('sparse', False)

        self.num_matrices = len(self.matrices.keys())
        self.matrix_hash = {}
        self.matrix_shape = 0
        self.titles = []
        self.report = []

    def doWork(self):
        if self.sparse:
            # Builds the hash
            self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.num_matrices)
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), "Building correspondence")
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), 0)
            indices = None
            p = 0
            for mat_name, mat in self.matrices.iteritems():
                # Gets all non-zero coordinates and makes sure that they are considered
                froms = mat[:,0]
                tos =  mat[:,1]

                if indices is None:
                    all_indices = np.hstack((froms, tos))
                else:
                    all_indices = np.hstack((indices, froms, tos))
                indices = np.unique(all_indices)
                p += 1
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), p)

            compact_shape = int(indices.shape[0])
            # Builds the hash
            for i in range(compact_shape):
                self.matrix_hash[indices[i]] = i
                self.titles.append(int(indices[i]))
        else:
            compact_shape = 0
            for mat_name, mat in self.matrices.iteritems():
                compact_shape = np.max(compact_shape, mat.shape[0])

            # Builds the hash
            self.matrix_hash = {i:i for i in range(compact_shape)}
            self.matrix.index = [i for i in range(compact_shape)]

        self.matrix = AequilibraeMatrix(zones=compact_shape, cores=self.num_matrices)
        self.matrix.matrix_hash = self.matrix_hash
        self.matrix.index = self.titles

        k = 0
        j = self.num_matrices * compact_shape
        m = 0
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), j)
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), "Reblocking matrices")
        for mat_name, mat in self.matrices.iteritems():
            if self.sparse:
                for i in range(compact_shape):
                    k += 1
                    mat[:,0][mat[:,0] == indices[i]] = self.matrix_hash[indices[i]]
                    mat[:,1][mat[:,1] == indices[i]] = self.matrix_hash[indices[i]]
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), k)
            else:
                k += self.num_matrices
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), 1)
            self.matrix.matrix[:,:,m] = coo_matrix((mat[:,2], (mat[:,0], mat[:,1])),
                                           shape=(compact_shape, compact_shape)).toarray().astype(np.float64)[:]
            self.matrix.names[mat_name] =  m
            m += 1
            del(mat)

        self.matrix.zones = compact_shape
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), "Matrix Reblocking finalized")
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), 'REBLOCKED MATRICES')


"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       AequilibraE Matrix
 Purpose:    Implements a new class to represent multi-layer matrices

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-06-25
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import numpy as np
from scipy.sparse import coo_matrix
import uuid
import tempfile
import os
from numpy.lib.format import open_memmap
import zipfile


# Necessary in case we are no the QGIS world
try:
    from common_tools.auxiliary_functions import logger
except:
    pass

class AequilibraeMatrix():
    def __init__(self, **kwargs):
        self.file_location = kwargs.get('path', tempfile.gettempdir())
        self.file_name = kwargs.get('file_name', 'aequilibrae_array_' + str(uuid.uuid4().hex) + '.npy')
        
        self.storage_path = None
        self.computation_path = os.path.join(self.file_location, self.file_name)

        self.zones = kwargs.get('zones', 1)

        self.num_matrices = kwargs.get('cores', 1)

        self.names = kwargs.get('names', ['mat'])

        self.data_type = kwargs.get('dtype', np.float32)

        self.matrix_hash = {}

        self.reserved_names = ['matrix', 'matrix_hash', 'data_type', 'names',
                               'num_matrice', 'zones', 'file_location', 'file_name']

        if self.names is None:
            self.names = []
            for i in range(self.num_matrices):
                self.names.append('matrix_' + str(i))
        else:
            if type(self.names) is list:
                if len(self.names) != self.num_matrices:
                    raise Exception('List of matrix names incompatible with number of matrices')
            else:
                if self.num_matrices == 1 and type(self.names) is str:
                    self.names = [self.names]
                else:
                    raise Exception('Matrix names need to be provided as a list')

            for reserved in self.reserved_names:
                if reserved in self.names:
                    raise Exception(reserved + ' is a reserved name')

        # sets the dtype
        dtype = [(x.encode('utf-8'), self.data_type) for x in self.names]
        dtype.append(('index', np.int32))

        # the shape
        shape = (self.zones,self.zones,)
        # the path
        matrix_path = os.path.join(self.file_location, self.file_name)
        self.matrix = open_memmap(matrix_path, mode='w+', dtype=dtype, shape=shape)


    def load(self, path_to_file):
        self.matrix = open_memmap(path_to_file, mode='r+')
        self.zones = self.matrix.shape[0]
        self.names = [x for i, x in self.matrix.dtype]
        self.names.pop('index')

    def __getitem__(self, mat_name):

        if mat_name == 'index':
            return self.matrix['index'][:,0]

        if mat_name in self.names:
            return self.matrix[mat_name]

        raise AttributeError("No such method or matrix core! --> " + str(mat_name))
    
    def save_to_disk(self, file_path= None, compressed=True):
            if compressed:
                compression = zipfile.ZIP_DEFLATED
            else:
                compression = zipfile.ZIP_STORED
        
            if file_path is not None:
                if file_path[-3:].lower() != 'aem':
                    file_path += '.aem'
            else:
                if self.storage_path is None:
                    raise AttributeError('No file name provided')
                else:
                    file_path = self.storage_path
                
            archive = zipfile.ZipFile(file_path, 'w', compression)
            archive.write(self.computation_path, os.path.basename(self.computation_path))
            archive.close()
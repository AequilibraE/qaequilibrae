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
import copy
from shutil import copyfile
import warnings

# CONSTANTS
VERSION = 1 # VERSION OF THE MATRIX FORMAT
INT = 0
FLOAT = 1
COMPLEX = 2
CORE_NAME_MAX_LENGTH=50
NOT_COMPRESSED = 0
COMPRESSED = 1

# Necessary in case we are no the QGIS world
# try:
#     from common_tools.auxiliary_functions import logger
# except:
#     pass

class AequilibraeMatrix():
    def __init__(self, file_name=None, zones=None, matrix_names=None, data_type=np.float64, compressed=False):
        self.reserved_names = ['reserved_names', 'file_path', 'zones', 'names', 'cores', 'data_type',
                               'compressed', '__version__', 'index', 'matrix', 'matrix_hash',
                               'rows', 'vector', 'columns', 'export']

        self.file_path = file_name
        self.zones = zones
        if matrix_names is None:
            self.names = ['mat']
        else:
            self.names = matrix_names
        self.cores = len(self.names)

        self.data_type = data_type
        data_size = np.dtype(data_type).itemsize

        # Matrix compression still not supported
        if compressed:
            compressed = False
            raise 'Matrix compression not yet supported'

        if compressed:
            self.compressed = COMPRESSED
        else:
            self.compressed = NOT_COMPRESSED

        if isinstance(self.names, list):
            pass
        else:
            raise Exception('Matrix names need to be provided as a list')

        for reserved in self.reserved_names:
            if reserved in self.names:
                raise Exception(reserved + ' is a reserved name')

        self.matrix = None
        self.index = None
        self.matrix_view = None
        self.view_names = None
        self.matrix_hash = {}

        if None not in [self.file_path, self.zones]:
            matrix_cells = self.zones * self.zones
            data_class = self.define_data_class()

            # Writes file version
            self.__version__ = VERSION

            # file version
            self.__set_matrix_elements__(offset = 0, dsize=(1), dtype='int8', values=[VERSION], overwrite=True)
            
            # If matrix is compressed or not
            self.__set_matrix_elements__(offset = 1, dsize=(1), dtype='int8', values=[self.compressed], overwrite=False)
            
            # number matrix cells if compressed
            self.__set_matrix_elements__(offset = 2, dsize=(1), dtype='int64', values=[matrix_cells], overwrite=False)

            # Zones
            self.__set_matrix_elements__(offset = 10, dsize=(1), dtype='int32', values=[self.zones], overwrite=False)
            
            # Matrix cores
            self.__set_matrix_elements__(offset=14, dsize=(1), dtype='int8', values=[self.cores], overwrite=False)
            
            # Data type
            self.__set_matrix_elements__(offset=15, dsize=(1), dtype='int8', values=[data_class], overwrite=False)
            
            # Data size
            self.__set_matrix_elements__(offset=16, dsize=(1), dtype='int8', values=[data_size], overwrite=False)
            
            # core names
            self.__set_matrix_elements__(offset=17, dsize=(self.cores), dtype='S' + str(CORE_NAME_MAX_LENGTH),
                                         values=self.names, overwrite=False)
            
            # Index
            self.__set_matrix_elements__(offset= 17 + CORE_NAME_MAX_LENGTH * self.cores, dsize=(self.zones),
                                         dtype='int64', values=[], overwrite=False)
            
            offset = 17 + CORE_NAME_MAX_LENGTH * self.cores + self.zones * 8
            if self.compressed:
                self.matrix = np.memmap(self.file_path, dtype=self.data_type, offset=offset, mode='r+', shape=(matrix_cells, self.cores + 2))
            else:
                self.matrix = np.memmap(self.file_path, dtype=self.data_type, offset=offset, mode='r+', shape=(self.zones, self.zones, self.cores))
            self.matrix.fill(0)
            self.matrix.flush()

            # Re-set index connection Index
            self.index = np.memmap(self.file_path, dtype='int64', offset=17 + CORE_NAME_MAX_LENGTH * self.cores, mode='r+', shape=(zones))
            self.index.fill(0)
            self.index.flush()


    def __set_matrix_elements__(self, offset, dsize, dtype, values, overwrite):
        if overwrite:
            fp = np.memmap(self.file_path, dtype=dtype, offset=offset, mode='w+', shape=(dsize))
        else:
            fp = np.memmap(self.file_path, dtype=dtype, offset=offset, mode='r+', shape=(dsize))
            
        for i, v in enumerate(values):
            fp[i] = v
        
        fp.flush()
        del fp
        
    def __getattr__(self, mat_name):
        if mat_name in self.names:
            return self.matrix[:, :, self.names.index(mat_name)]

        raise AttributeError("No such method or matrix core! --> " + str(mat_name))

    def compress(self):
        pass
    def decompress(self):
        pass

    def close(self, flush=True):
        if flush:
            self.matrix.flush()
            self.index.flush()
        del self.matrix
        del self.index
            
    def export(self, output_name, cores = None):
        extension = output_name.upper()[-3:]
        if cores is None:
            cores = self.names

        if extension == 'CSV':
            names = self.view_names
            self.computational_view(cores)
            output = open(output_name, 'w')

            titles = ['row', 'column']
            for core in self.view_names:
                titles.append(core)
            print >> output, ','.join(titles)

            for i in range(self.zones):
                for j in range(self.zones):
                    record = [self.index[i], self.index[j]]
                    if len(self.view_names) > 1:
                        record.extend(self.matrix_view[i,j,:])
                    else:
                        record.append(self.matrix_view[i,j])
                    print >> output, ','.join(str(x) for x in record)
            output.flush()
            output.close()
            self.computational_view(names)
        else:
            warnings.warn('File extension not implemented yet')

    def load(self, file_path):
        self.file_path = file_path

        data_class = self.define_data_class()

        # GET File version
        fp = np.memmap(self.file_path, dtype='int8', offset=0, mode='r+', shape=(1))
        self.__version__ = fp[0]
        if self.__version__ != VERSION:
            raise ValueError ('Matrix formats do not match')
        del fp

        # If matrix is compressed or not
        fp = np.memmap(self.file_path, dtype='int8', offset=1, mode='r+', shape=(1))
        self.compressed = fp[0]
        del fp

        # number matrix cells if compressed
        fp = np.memmap(self.file_path, dtype='int64', offset=2, mode='r+', shape=(1))
        matrix_cells = fp[0]
        del fp

        # Zones
        fp = np.memmap(self.file_path, dtype='int32', offset=10, mode='r+', shape=(1))
        self.zones = fp[0]
        del fp

        # Matrix cores
        fp = np.memmap(self.file_path, dtype='int8', offset=14, mode='r+', shape=(1))
        self.cores = fp[0]
        del fp

        # Data type
        fp = np.memmap(self.file_path, dtype='int8', offset=15, mode='r+', shape=(1))
        data_class = fp[0]
        del fp

        # Data size
        fp = np.memmap(self.file_path, dtype='int8', offset=16, mode='r+', shape=(1))
        data_size = fp[0]
        del fp

        if data_class == INT:
            if data_size == 1:
                self.data_type = np.int8
            elif data_size == 2:
                self.data_type = np.int16
            elif data_size == 4:
                self.data_type = np.int32
            elif data_size == 8:
                self.data_type = np.int64
            elif data_size == 16:
                self.data_type = np.int128

        if data_class == FLOAT:
            if data_size == 1:
                self.data_type = np.float8
            elif data_size == 2:
                self.data_type = np.float16
            elif data_size == 4:
                self.data_type = np.float32
            elif data_size == 8:
                self.data_type = np.float64
            elif data_size == 16:
                self.data_type = np.float128

        # core names
        fp = np.memmap(self.file_path, dtype='S' + str(CORE_NAME_MAX_LENGTH), offset=17, mode='r+', shape=(self.cores))
        self.names = []
        for i in range(self.cores):
            self.names.append(fp[i])
        del fp

        # Index
        offset = 17 + CORE_NAME_MAX_LENGTH * self.cores
        self.index = np.memmap(self.file_path, dtype='int64', offset=offset, mode='r+', shape=(self.zones))

        # DATA
        offset += self.zones * 8
        if self.compressed:
            self.matrix = np.memmap(self.file_path, dtype=self.data_type, offset=offset, mode='r+', shape=(matrix_cells, self.cores + 2))
        else:
            self.matrix = np.memmap(self.file_path, dtype=self.data_type, offset=offset, mode='r+', shape=(self.zones, self.zones, self.cores))


    def computational_view(self, core_list = None):
        self.matrix_view = None
        self.view_names = None
        if core_list is None:
            core_list = self.names
        else:
            if isinstance(core_list, list):
                for i in core_list:
                    if i not in self.names:
                        raise ValueError('Matrix core {} no available on this matrix').format(i)

                if len(core_list) > 1:
                    for i, x in enumerate(core_list[1:]):
                        k = self.names.index(x) # index of the first element
                        k0 = self.names.index(core_list[i]) # index of the first element
                        if k-k0 != 1:
                            raise ValueError('Matrix cores {} and {} are not adjacent').format(core_list[i-1], x)
            else:
                raise TypeError('Please provide a list of matrices')

        self.view_names = core_list
        if len(core_list) == 1:
            self.matrix_view = self.matrix[:, :, self.names.index(core_list[0]):self.names.index(core_list[0])+1]
        elif len(core_list) > 1:
            self.matrix_view = self.matrix[:, :, self.names.index(core_list[0]):self.names.index(core_list[-1])+1]

    def copy(self, output_name, cores=None, compress=None):

        if cores is None:

            copyfile(self.file_path, output_name)
            output = AequilibraeMatrix()
            output.load(output_name)
            if self.view_names is not None:
                output.computational_view(self.view_names)

            if compress is not None:
                if compress != self.compressed:
                    if compress:
                        output.compress()
                    else:
                        output.decompress()
        else:
            if compress is None:
                compress = self.compressed

            if not isinstance(cores, list):
                raise ValueError('Cores need to be presented as list')

            for i in cores:
                if i not in self.names:
                    raise ValueError('Matrix core {} not available on this matrix').format(i)

            output = AequilibraeMatrix(file_name=output_name,
                                       zones=self.zones,
                                       matrix_names=cores,
                                       data_type=self.data_type,
                                       compressed=bool(self.compressed))

            output.index[:] = self.index[:]
            for i, c in enumerate(cores):
                output.matrix[:, :, i] = self.matrix[:, :, self.names.index(c)]

            output.matrix.flush()

        return output

    def rows(self):
        return self.vector(axis=0)

    def columns(self):
        return self.vector(axis=1)

    def vector(self, axis):
        if self.view_names is None:
            raise ReferenceError('Matrix is not set for computation')
        if len(self.view_names) > 1:
            raise ValueError('Vector for a multi-core matrix is ambiguous')

        return self.matrix_view.astype(np.float).sum(axis=axis)[:,0]

    def __builds_hash__(self):
        return {self.index[i]: i for i in range(self.zones)}

    def define_data_class(self):
        if self.data_type in [np.float16, np.float32, np.float64]:
            data_class = FLOAT

        if self.data_type in [np.int8, np.int16, np.int32, np.int64]:
            data_class = INT

        return data_class
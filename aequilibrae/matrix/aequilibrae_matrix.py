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
import copy

import warnings

# Necessary in case we are no the QGIS world
# try:
#     from common_tools.auxiliary_functions import logger
# except:
#     pass

class AequilibraeMatrix():
    def __init__(self, **kwargs):
        self.file_location = kwargs.get('path', tempfile.gettempdir())
        self.file_name = kwargs.get('file_name', 'aequilibrae_array_' + str(uuid.uuid4().hex) + '.npy')
        
        self.storage_path = None
        self.computation_path = os.path.join(self.file_location, self.file_name)

        self.zones = kwargs.get('zones', 1)

        self.cores = kwargs.get('cores', 1)

        self.names = kwargs.get('names')

        self.data_type = kwargs.get('dtype', np.float64)

        self.matrix_hash = {}

        self.reserved_names = ['matrix_procedures', 'matrix_hash', 'data_type', 'names',
                               'num_matrice', 'zones', 'file_location', 'file_name', 'storage_path',
                               'rows', 'vector', 'columns', 'export']

        # methods that will be used for computation
        self.matrix_view = None
        self.view_names = None


        if self.names is None:
            self.names = []
            for i in range(self.cores):
                self.names.append('matrix_' + str(i))
        else:
            if type(self.names) is list:
                if len(self.names) != self.cores:
                    raise Exception('List of matrix_procedures names incompatible with number of matrices')
            else:
                if self.cores == 1 and type(self.names) is str:
                    self.names = [self.names]
                else:
                    raise Exception('Matrix names need to be provided as a list')

            for reserved in self.reserved_names:
                if reserved in self.names:
                    raise Exception(reserved + ' is a reserved name')

        # sets the dtype
        dtype = [(x.encode('utf-8'), self.data_type) for x in self.names]
        dtype.append(('index', np.int64))

        # the shape
        shape = (self.zones,self.zones,)

        self.matrix = open_memmap(self.computation_path, mode='w+', dtype=dtype, shape=shape)

    def __getattr__(self, mat_name):

        if mat_name == 'index':
            return self.matrix['index'][:,0]

        if mat_name.lower() == 'matrix_procedures':
            return self.matrix

        if mat_name in self.names:
            return self.matrix[mat_name]

        raise AttributeError("No such method or matrix_procedures core! --> " + str(mat_name))

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

            # saves
            archive.write(self.computation_path, os.path.basename(file_path)[:-3]+'npy')
            archive.close()

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
                        record.extend(self.matrix_view[i,j,:][0])
                    else:
                        record.append(self.matrix_view[i,j][0])
                    print >> output, ','.join(str(x) for x in record)
            output.flush()
            output.close()
            self.computational_view(names)
        else:
            warnings.warn('File extension not implemented yet')

    def load(self, file_path):
        f = open(file_path)
        self.storage_path = os.path.realpath(f.name)
        f.close()

        self.file_location = tempfile.gettempdir()
        # We use a random file name for computation to be able to handle multiple matrices with the same name
        # at the same time
        self.file_name = 'aequilibrae_array_' + str(uuid.uuid4().hex) + '.npy'
        self.computation_path = os.path.join(self.file_location, self.file_name)

        # Extract and rename it
        zip_ref = zipfile.ZipFile(self.storage_path, 'r')
        zip_ref.extractall(self.file_location)
        zip_ref.close()
        os.rename(os.path.join(self.file_location, os.path.basename(self.storage_path)[:-3]+'npy'), self.computation_path)

        # Map in memory and load matrix_procedures names plus dimensions
        self.matrix = open_memmap(self.computation_path, mode='r+')
        self.zones = self.matrix.shape[0]
        self.names = [x for x in self.matrix.dtype.fields if x != 'index']
        self.cores = len(self.names)
        self.data_type = self.matrix.dtype[0]
        self.matrix_hash = self.__builds_hash__()

    def computational_view(self, core_list = None):
        if core_list is None:
            core_list = self.names
        if isinstance(core_list, list):

            view_dtype = np.dtype({core:self.matrix.dtype.fields[core] for core in core_list})
            self.matrix_view = np.ndarray(self.matrix.shape, view_dtype, self.matrix, 0, self.matrix.strides)

            # partial_mat = self.matrix[core_list]
            # self.matrix_view = partial_mat.view(np.float64).reshape(partial_mat.shape + (-1,))
            self.view_names = core_list
        else:
            self.matrix_view = None
            self.view_names = None
            raise ('Please provide a list of matrices')

    def copy(self, cores=None, names=None):

        if cores is None: cores = self.names

        if not isinstance(cores, list):
            raise ValueError('Cores need to be presented as list')

        if names is None:
            names = copy.deepcopy(cores)
            if not isinstance(names, list):
                raise ValueError('names need to be presented as list')

            if len(cores) != len(names):
                raise ValueError('Cores to copy and list of names needs to have the same length')

        output = AequilibraeMatrix(zones=self.zones,
                                   cores=len(names),
                                   names=names,
                                   data_type=self.data_type)

        output.index[:] = self.index[:]
        for name, new_name in zip(cores, names):
            output.matrix[new_name][:, :] = self.matrix[name][:, :]
            name_dict = {name: new_name}
        output.__builds_hash__()

        if self.view_names is not None:
            new_view_names = [name_dict[name] for name in self.view_names if name in cores]
            if new_view_names:
                output.computational_view(new_view_names)

        return output

    def rows(self):
        return self.vector(axis=0)

    def columns(self):
        return self.vector(axis=1)

    def vector(self, axis):
        if self.view_names is None:
            raise ReferenceError('Matrix is not set for computation')
        if len(self.view_names) > 1:
            raise ReferenceError('Vector for a multi-core matrix is ambiguous')

        return np.sum(self.matrix_view[:,:,0], axis=axis)

    def __builds_hash__(self):
        return {self.index[i]: i for i in range(self.zones)}
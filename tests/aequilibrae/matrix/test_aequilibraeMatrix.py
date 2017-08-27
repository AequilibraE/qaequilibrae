from unittest import TestCase
import os
import tempfile

import numpy as np

from aequilibrae.matrix import AequilibraeMatrix

zones = 100
path_test =tempfile.gettempdir()
name_test = 'aequilibrae_matrix_test.npy'
new_matrix = None

class TestAequilibraeMatrix(TestCase):
    def test___init__(self):
        args = {'path': path_test,
                'file_name': name_test,
                'zones': zones,
                'cores': 2,
                'names': ['mat', 'seed']}

        matrix = AequilibraeMatrix(**args)

        matrix.index[:] = np.arange(matrix.zones) + 100
        matrix.mat[:,:] = np.random.rand(matrix.zones,matrix.zones)[:,:]
        matrix.mat[:,:] = matrix.mat[:,:] * (1000 / np.sum(matrix.mat[:,:]))

        # It also tests saving to disl
        matrix.save_to_disk(os.path.join(path_test, name_test[:-3] + 'aem'))
        del(matrix)

    def test_load(self):
        self.new_matrix = AequilibraeMatrix()
        self.new_matrix.load(os.path.join(path_test, name_test[:-3] + 'aem'))

    def test_computational_view(self):
        self.test_load()
        self.new_matrix.computational_view(['mat', 'seed'])
        if self.new_matrix.matrix_view.shape[2] != 2:
            self.fail('Computational view returns the wrong number of matrices')

    def test_copy(self):
        self.test_load()
        if round(self.new_matrix.mat.sum(),0) != 1000:
            self.fail('Matrix totals was not maintained')

        if not np.array_equal(self.new_matrix.index, np.arange(zones) + 100):
            self.fail('Matrix indices was not maintained')

        # test in-memory matrix_procedures copy
        matrix_copy = self.new_matrix.copy(cores=['mat'], names=['copy_mat'])

        matrix_copy.storage_path = self.new_matrix.storage_path
        matrix_copy.file_location = self.new_matrix.file_location
        matrix_copy.file_name = self.new_matrix.file_name

        if not np.array_equal(matrix_copy.copy_mat, self.new_matrix.mat):
            self.fail('Matrix copy was not perfect')

        if matrix_copy.names != ['copy_mat']:
            self.fail('Wrong number of cores were copied')
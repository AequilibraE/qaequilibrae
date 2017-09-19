from unittest import TestCase
import os
import tempfile

import numpy as np

from aequilibrae.matrix import AequilibraeMatrix

zones = 50
path_test =tempfile.gettempdir()
path_test ='D:/'
name_test = 'aequilibrae_matrix_test.aem'
name_test = os.path.join(path_test, name_test)
copy_matrix_name = os.path.join(path_test, 'aequilibrae_new_matrix_test.aem')
csv_export_name = os.path.join(path_test, 'aequilibrae_test_export_matrix.csv')
class TestAequilibraeMatrix(TestCase):
    def test___init__(self):
        os.remove(name_test) if os.path.exists(name_test) else None
        args = {'file_name': name_test,
                'zones': zones,
                'matrix_names': ['mat', 'seed', 'dist']}

        matrix = AequilibraeMatrix(**args)

        matrix.index[:] = np.arange(matrix.zones) + 100
        matrix.mat[:,:] = np.random.rand(matrix.zones,matrix.zones)[:,:]
        matrix.mat[:,:] = matrix.mat[:,:] * (1000 / np.sum(matrix.mat[:,:]))
        matrix.close(True)
        del(matrix)
        
    def test_load(self):
        # self.test___init__()
        self.new_matrix = AequilibraeMatrix()
        self.new_matrix.load(name_test)

    def test_computational_view(self):
        self.test_load()
        self.new_matrix.computational_view(['mat', 'seed'])
        self.new_matrix.mat.fill(0)
        self.new_matrix.seed.fill(0)
        if self.new_matrix.matrix_view.shape[2] != 2:
            self.fail('Computational view returns the wrong number of matrices')

        self.new_matrix.computational_view(['mat'])
        self.new_matrix.matrix_view[:, :, 0] = np.arange(zones**2).reshape(zones, zones)
        if np.sum(self.new_matrix.mat) != np.sum(self.new_matrix.matrix_view):
            self.fail('Assigning to matrix view did not work')
        self.new_matrix.close(True)
        
    def test_copy(self):
        self.test_load()

        # test in-memory matrix_procedures copy
        
        matrix_copy = self.new_matrix.copy(copy_matrix_name, cores=['mat'])

        if not np.array_equal(matrix_copy.mat, self.new_matrix.mat):
            self.fail('Matrix copy was not perfect')
        matrix_copy.close(True)
        self.new_matrix.close(True)
    def test_export(self):
        self.test_load()
        self.new_matrix.export(csv_export_name)
        self.new_matrix.close(True)
from aequilibrae.matrix import AequilibraeMatrix
import tempfile
import numpy as np
import uuid
import os
from clean_after_tests import clean_after_tests

zones = 100
path_test =tempfile.gettempdir()
name_test = 'aequilibrae_matrix_test.npy'
args = {'path': path_test,
    'file_name': name_test,
    'zones': zones,
    'cores': 2,
    'names': ['mat', 'seed']}

matrix = AequilibraeMatrix(**args)

matrix.index[:] = np.arange(matrix.zones) + 100
matrix.mat[:,:] = np.random.rand(matrix.zones,matrix.zones)[:,:]
tot = matrix.mat.sum()

matrix.save_to_disk(os.path.join(path_test, name_test[:-3] + 'aem'))
del(matrix)

new_matrix = AequilibraeMatrix()
new_matrix.load(os.path.join(path_test, name_test[:-3] + 'aem'))

if tot != new_matrix.mat.sum():
    raise ValueError('Matrix totals was not maintained')

if not np.array_equal(new_matrix.index, np.arange(zones) + 100):
    raise ValueError('Matrix indices was not maintained')

# test in-memory matrix copy
matrix_copy = new_matrix.copy()

if tot != matrix_copy.mat.sum():
    raise ValueError('Matrix totals for copy was not maintained')

if not np.array_equal(matrix_copy.index, np.arange(zones) + 100):
    raise ValueError('Matrix indices for copy was not maintained')


clean_after_tests()
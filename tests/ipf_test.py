from aequilibrae.matrix import AequilibraEData, AequilibraeMatrix
from aequilibrae.distribution import Ipf
import tempfile
import numpy as np
import uuid
import os
from clean_after_tests import clean_after_tests

zones = 100

# row vector
args = {'entries': zones,
        'fields': ['rows'],
        'types': [np.float64]}
row_vector = AequilibraEData(**args)
row_vector.rows[:] = np.random.rand(zones)[:] * 1000

# column vector
args['fields'] = ['columns']
column_vector = AequilibraEData(**args)
column_vector.columns[:] = np.random.rand(zones)[:] * 1000

# balance vectors
column_vector.columns[:] = column_vector.columns[:] * (row_vector.rows.sum()/column_vector.columns.sum())

# seed matrix
args = {'zones': zones,
        'cores': 1,
        'names': ['seed']}

matrix = AequilibraeMatrix(**args)
matrix.seed[:, :] = np.random.rand(zones, zones)[:,:]
matrix.computational_view(['seed'])



# The IPF per se
args = {'matrix': matrix,
        'rows': row_vector,
        'row_field': 'rows',
        'columns': column_vector,
        'column_field': 'columns'}

fratar = Ipf(**args)
fratar.fit()

result = fratar.output

if result.seed.sum() != result.seed.sum():
    raise ValueError('Ipf did not converge')

if fratar.gap > fratar.parameters['convergence level']:
    raise ValueError('Ipf did not converge')

clean_after_tests()
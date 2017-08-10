from aequilibrae.matrix import AequilibraEData
import tempfile
import numpy as np
import uuid
import os
from clean_after_tests import clean_after_tests

# Generates the dataset
path_test =tempfile.gettempdir()
name_test = 'aequilibrae_database_' + str(uuid.uuid4().hex) + '.aed'
args = {'file_path': path_test,
    'file_name': name_test,
    'entries': 100,
    'fields': ['d', 'data2', 'data3'],
    'types': [np.float64, np.float32, np.int8]}

dataset = AequilibraEData(**args)

dataset.index[:] = np.arange(dataset.entries) + 100
dataset.d[:] = dataset.index[:]**2

# removes the dataset
del(dataset)

# re-imports the dataset
a = AequilibraEData()
a.load(os.path.join(path_test, name_test))


# checks if the values were properly saved
if a.index[70] != 170:
    raise AttributeError("Value for data index test was not as expected")

if int(a.d[70]) != 28900:
    raise AttributeError("Value for data field test was not as expected")

clean_after_tests()
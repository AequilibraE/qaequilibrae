import os
import tempfile
import uuid
from unittest import TestCase

import numpy as np

from aequilibrae.matrix import AequilibraEData

file_path = AequilibraEData().random_name()

class TestAequilibraEData(TestCase):
    def test___init__(self):
        # Generates the dataset
        args = {'file_path': file_path,
                'entries': 100,
                'field_names': ['d', 'data2', 'data3'],
                'data_types': [np.float64, np.float32, np.int8]}

        dataset = AequilibraEData(**args)

        dataset.index[:] = np.arange(dataset.entries) + 100
        dataset.d[:] = dataset.index[:]**2

        if dataset.index[70] != 170:
            self.fail()

        if int(dataset.d[70]) != 28900:
            self.fail()

        # removes the dataset
        del(dataset)

    def test_load(self):
        # re-imports the dataset
        a = AequilibraEData()
        a.load(file_path)


        # checks if the values were properly saved
        if a.index[70] != 170:
            self.fail("Value for data index test was not as expected")

        if int(a.d[70]) != 28900:
            self.fail("Value for data field test was not as expected")
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
from common_tools.auxiliary_functions import logger
from numpy.lib.format import open_memmap

class AequilibraeMatrix():
    def __init__(self, **kwargs):
        self.file_location = kwargs.get('path', tempfile.gettempdir())
        self.file_name = kwargs.get('file_name', 'aequilibrae_array_' + str(uuid.uuid4().hex) + '.aem')

        self.zones = kwargs.get('zones', 0)
        self.matrix_hash = {}
        self.index = []
        self.num_matrices = kwargs.get('cores', 1)

        self.matrix = np.memmap(os.path.join(self.file_location, self.file_name),
                                dtype=np.float64,
                                mode='w+',
                                shape=(self.zones, self.zones, self.num_matrices))

        self.names = {}

    def load_from_disk(self, path_to_file):
        pass
        # self.matrix = np.memmap(os.path.join(self.file_location, self.file_name),
        #                         dtype=np.float64,
        #                         mode='r+',
        #                         shape=(self.zones, self.zones, self.num_matrices))
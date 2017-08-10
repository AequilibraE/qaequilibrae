"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       AequilibraE Database
 Purpose:    Implements a class to represent flat databases with an unique id field.
             It is really just a wrapper around numpy recarray memmap

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
import uuid
import tempfile
import os
from numpy.lib.format import open_memmap

# Necessary in case we are no the QGIS world
# try:
#     from common_tools.auxiliary_functions import logger
# except:
#     pass


class AequilibraEData():
    def __init__(self, **kwargs):
        self.file_path = kwargs.get('file_path', tempfile.gettempdir())
        self.file_name = kwargs.get('file_name', 'aequilibrae_database_' + str(uuid.uuid4().hex) + '.aed')

        self.aeq_index_type = np.int64

        self.complete_path = os.path.join(self.file_path, self.file_name)

        self.entries = kwargs.get('entries', 1)

        self.fields = kwargs.get('fields', 'default_data')

        self.data_types = kwargs.get('types', np.float64)


        """TODO:
        list the appropriate reserved names"""
        self.reserved_names = ['file_path', 'file_name', 'complete_path', 'entries', 'data',
                               'fields', 'data_types', 'num_fields', 'reserved_names', 'aeq_index_type']
        if isinstance(self.fields, str):
            self.fields = [self.fields]

        if isinstance(self.data_types, type):
            self.data_types = [self.data_types]

        if not isinstance(self.fields, list) or not isinstance(self.data_types, list):
            raise Exception('Fields names and data types need to be lists')

        self.num_fields = len(self.fields)

        if len(self.data_types) != self.num_fields:
            raise Exception('Lists of fields and types need to have the same dimension')

        if 'index' in self.fields:
            if self.data_types[self.fields.index("index")] != self.aeq_index_type:
                raise Exception('Index type needs to be NumPY int64')
        else:
            self.fields = ['index'] + self.fields
            self.data_types = [self.aeq_index_type] + self.data_types

        dtype = [(self.fields[i].encode('utf-8'), self.data_types[i]) for i in range(self.num_fields + 1)]

        for field in self.fields:
            if field in self.reserved_names:
                raise Exception(field + ' is a reserved name. You cannot use it as a field name')

        # the file
        self.data = open_memmap(self.complete_path, mode='w+', dtype=dtype, shape=(self.entries,))

    def __getattr__(self, field_name):

        if field_name == 'index':
            return self.data['index']

        if field_name.lower() == 'data':
            return self.data

        if field_name in self.fields:
            return self.data[field_name]

        raise AttributeError("No such method or data field! --> " + str(field_name))

    def load(self, file_path):
        f = open(file_path)
        self.complete_path = os.path.realpath(f.name)
        f.close()

        self.file_path, self.file_name = os.path.split(self.complete_path)

        # Map in memory and load matrix names plus dimensions
        self.data = open_memmap(self.complete_path, mode='r+')

        self.entries = self.data.shape[0]
        self.fields = [x for x in self.data.dtype.fields if x != 'index']
        self.num_fields = len(self.fields)
        self.data_types = [self.data[x].dtype.type for x in self.fields]
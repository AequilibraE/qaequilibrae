"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loads vectors from file/layer
 Purpose:    Implements vector loading

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-08-15
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *
from PyQt4.QtCore import *
import numpy as np
from ..common_tools.worker_thread import WorkerThread
import struct
from ..aequilibrae.matrix import AequilibraEData
from ..common_tools.global_parameters import *
from ..common_tools import logger

class LoadVector(WorkerThread):
    def __init__(self, parentThread, layer, index_field, fields, file_name):
        WorkerThread.__init__(self, parentThread)
        self.layer = layer
        self.index_field = index_field
        self.fields = fields
        self.error = None
        self.python_version = (8 * struct.calcsize("P"))
        self.output = AequilibraEData()
        self.output_name = file_name

    def doWork(self):
        feat_count = self.layer.featureCount()
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (feat_count))

        # Create specification for the output file
        datafile_spec = {}
        datafile_spec['entries'] = feat_count
        if self.output_name is None:
            datafile_spec['memory_mode'] = True
        else:
            datafile_spec['memory_mode'] = False
        fields = []
        types = []
        idxs = []
        for field in self.layer.dataProvider().fields().toList():
            if field.name() in self.fields:
                if field.type() in integer_types:
                    types.append('<i8')
                elif field.type() in float_types:
                    types.append('<f8')
                elif field.type() in string_types:
                    types.append('S' + str(field.length()))
                else:
                    print field.type()
                    self.error = 'Field {} does has a type not supported.'.format(str(field.name()))
                    break
                fields.append(str(field.name()))
                idxs.append(self.layer.fieldNameIndex(field.name()))

        index_idx = self.layer.fieldNameIndex(self.index_field)
        datafile_spec['field_names'] = fields
        datafile_spec['data_types'] = types
        datafile_spec['file_path'] = self.output_name

        if self.error is None:
            logger(fields)
            logger(types)
            self.output.create_empty(**datafile_spec)

            # Get all the data
            for p, feat in enumerate(self.layer.getFeatures()):
                for idx, field in zip(idxs, fields):
                    if not isinstance(feat.attributes()[idx], QPyNullVariant):
                        self.output.data[field][p] = feat.attributes()[idx]
                self.output.index[p] = feat.attributes()[index_idx]
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (p))


            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(feat_count)))
        else:
            self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), 'Vector loaded')
            # qgis.utils.iface.messageBar().pushMessage(self.error)
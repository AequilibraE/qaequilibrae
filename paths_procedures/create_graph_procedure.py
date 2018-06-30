"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Creating the graph from geographic layer
 Purpose:    Threaded procedure for creating the graph

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *
from PyQt4.QtCore import *
import time
import numpy as np
import sys
import os
import struct

from aequilibrae import reserved_fields
from aequilibrae.paths import Graph
from ..common_tools import WorkerThread, reporter, logger

class GraphCreation(WorkerThread):
    def __init__(self, parentThread, net_layer, link_id, direction_field,
                       fields_to_add, selected_only, centroids):
        WorkerThread.__init__(self, parentThread)
        self.net_layer = net_layer
        self.link_id = link_id
        self.direction_field = direction_field
        self.fields_to_add = fields_to_add
        self.selected_only = selected_only
        self.features = None
        self.error = None
        self.centroids = centroids
        self.report = []
        self.feat_count = 0

        self.bi_directional = False
        if direction_field is not None:
            self.bi_directional = True

    def doWork(self):
        if self.selected_only:
            self.features = self.net_layer.selectedFeatures()
            self.feat_count = self.net_layer.selectedFeatureCount()
        else:
            self.features = self.net_layer.getFeatures()
            self.feat_count = self.net_layer.featureCount()

        # Checking ID uniqueness
        self.report.append(reporter("Checking ID uniqueness", 0))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),"Checking ID uniqueness. Please wait")
        all_ids = self.net_layer.uniqueValues(self.link_id)

        if NULL in all_ids:
            self.error = "ID field has NULL values"
            self.report.append(self.error)
        else:
            if len(all_ids) < self.feat_count:
                self.error = 'IDs are not unique.'
                self.report.append(self.error)

        if self.error is None:
            self.report.append(reporter('Loading data from layer', 0))
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),"Loading data from layer")
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), 0)
            self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.feat_count)

            self.graph = Graph()
            all_types = [self.graph._Graph__integer_type, self.graph._Graph__integer_type, self.graph._Graph__integer_type, np.int8]
            all_titles = [reserved_fields.link_id, reserved_fields.a_node, reserved_fields.b_node, reserved_fields.direction]

            for name_field, values in self.fields_to_add.iteritems():
                all_titles.append((name_field + '_ab').encode('ascii','ignore'))
                all_types.append(np.float64)
                all_titles.append((name_field + '_ba').encode('ascii','ignore'))
                all_types.append(np.float64)

            dt = [(t, d) for t, d in zip(all_titles, all_types)]

            a_node = self.net_layer.fieldNameIndex(reserved_fields.a_node)
            b_node = self.net_layer.fieldNameIndex(reserved_fields.b_node)
            data = []

            for p, feat in enumerate(self.features):
                line = []
                line.append(feat.attributes()[self.link_id])
                line.append(feat.attributes()[a_node])
                line.append(feat.attributes()[b_node])
                if self.bi_directional:
                    line.append(feat.attributes()[self.direction_field])
                else:
                    line.append(1)

                # We append the data fields now
                for k, v in self.fields_to_add.iteritems():
                    a, b = v
                    line.append(feat.attributes()[a])
                    if self.bi_directional:
                        line.append(feat.attributes()[b])
                    else:
                        line.append(-1)

                for k in line:
                    if k == NULL:
                        t = ','.join([str(x) for x in line])
                        self.error = 'Field with NULL value - ID:' + str(line[0]) + "  /  " + t
                        break
                if self.error is not None:
                    break
                data.append(line)

                if p % 50 == 0:
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), p)

            if self.error is None:
                self.report.append(reporter('Converting data to graph', 0))
                network = np.asarray(data)

                self.graph.network = np.zeros(network.shape[0], dtype=dt)

                for k, t in enumerate(dt):
                    self.graph.network[t[0]] = network[:,k].astype(t[1])
                del network

                self.graph.type_loaded = 'NETWORK'
                self.graph.status = 'OK'
                self.graph.network_ok = True
                self.graph.prepare_graph(self.centroids)
                self.graph.__source__ = None
                self.graph.__field_name__ = None
                self.graph.__layer_name__ = None

                self.report.append(reporter('Process finished', 0))
            else:
                self.report.append(self.error)
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), None)
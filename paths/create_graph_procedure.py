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

import  aequilibrae.reserved_fields as reserved_fieds
from aequilibrae.paths import Graph
from ..common_tools import WorkerThread

class GraphCreation(WorkerThread):
    def __init__(self, parentThread, net_layer, link_id, direction_field, fields_to_add, selected_only):
        WorkerThread.__init__(self, parentThread)
        self.net_layer = net_layer
        self.link_id = link_id
        self.direction_field = direction_field
        self.fields_to_add = fields_to_add
        self.selected_only = selected_only
        self.features = None
        self.error = None
        self.python_version = (8 * struct.calcsize("P"))

        self.bi_directional = False
        if direction_field is not None:
            self.bi_directional = True

        if self.selected_only:
            self.feat_count = self.net_layer.selectedFeatureCount()
        else:
            self.feat_count = self.net_layer.featureCount()

    def doWork(self):
        # Checking ID uniqueness
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),"Checking ID uniqueness")
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.feat_count)

        a = []
        all_ids = np.zeros(self.feat_count, dtype=np.int_)

        if self.selected_only:
            self.features = self.net_layer.selectedFeatures()
        else:
            self.features = self.net_layer.getFeatures()

        p = 0
        for feat in self.features:
            k = feat.attributes()[self.link_id]
            if k == NULL:
                self.error = "ID field has NULL values"
                break
            else:
                all_ids[p] = k
                p += 1
                if p % 50 == 0:
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), p)
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), self.feat_count)

        if self.error is None:
            # Checking uniqueness
            if self.python_version == 32: # controlling for Numpy's weird behavior on bincount
                y = np.bincount(all_ids.astype(np.int32))
            else:
                y = np.bincount(all_ids)

            if np.max(y) > 1:
                self.error = 'IDs are not unique.'

        if self.error is None:
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),"Loading data from layer")
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), 0)

            self.graph = Graph()

            all_types = [np.int32, np.int32, np.int32, np.int8]
            all_titles = ['link_id', reserved_fieds.a_node, reserved_fieds.b_node, 'direction']

            for name_field, values in self.fields_to_add.iteritems():
                all_types.append(np.float64)
                all_titles.append((name_field + '_ab').encode('ascii','ignore'))
                all_types.append(np.float64)
                all_titles.append((name_field + '_ba').encode('ascii','ignore'))

            dt = [(t, d) for t, d in zip(all_titles, all_types)]

            a_node = self.net_layer.fieldNameIndex(reserved_fieds.a_node)
            b_node = self.net_layer.fieldNameIndex(reserved_fieds.b_node)
            data = []

            if self.selected_only:
                self.features = self.net_layer.selectedFeatures()
            else:
                self.features = self.net_layer.getFeatures()

            p = 0
            for feat in self.features:
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
                        t = ''
                        for j in line:
                            t = t + ',' + str(j)
                        self.error = 'Field with NULL value - ID:' + str(line[0]) + "  /  " + t
                        break
                if self.error is not None:
                    break
                data.append(line)

                p += 1
                if p % 50 == 0:
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), p)

            if self.error is None:
                network = np.asarray(data)

                self.graph.network = np.zeros(network.shape[0], dtype=dt)

                for k, t in enumerate(dt):
                    self.graph.network[t[0]] = network[:,k].astype(t[1])
                del network

                self.graph.type_loaded = 'NETWORK'
                self.graph.status = 'OK'
                self.graph.network_ok = True
                self.graph.prepare_graph()
                self.graph.__source__ = None
                self.graph.__field_name__ = None
                self.graph.__layer_name__ = None

        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), None)
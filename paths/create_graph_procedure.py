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

from aequilibrae.paths import Graph
from worker_thread import WorkerThread

class GraphCreation(WorkerThread):
    def __init__(self, parentThread, netlayer, linkid, ablength, bidirectional, directionfield, balength, skims, selected_only, featcount):
        WorkerThread.__init__(self, parentThread)
        self.netlayer = netlayer
        self.linkid = linkid
        self.ablength = ablength
        self.balength = balength
        self.bidirectional = bidirectional
        self.directionfield = directionfield
        self.skims = skims
        self.selected_only = selected_only
        self.features = None
        self.featcount =  featcount
        self.error = None

    def doWork(self):
        # Checking ID uniqueness
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),"Checking ID uniqueness")
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.featcount)

        a = []
        all_ids = np.zeros(self.featcount, dtype=np.int_)

        if self.selected_only:
            self.features = self.netlayer.selectedFeatures()
        else:
            self.features = self.netlayer.getFeatures()

        p = 0
        for feat in self.features:
            k = feat.attributes()[self.linkid]
            if k == NULL:
                self.error = "ID field has NULL values"
                break
            else:
                all_ids[p] = k
                p += 1
                if p % 50 == 0:
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), p)
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), self.featcount)

        if self.error is None:
            # Checking uniqueness
            y = np.bincount(all_ids)
            if np.max(y) > 1:
                self.error = 'IDs are not unique.'

        if self.error is None:
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),"Loading data from layer")
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), 0)

            self.graph = Graph()

            all_types = [np.int64, np.int64, np.int64, np.float64, np.float64, np.int64]
            all_titles = ['link_id', 'a_node', 'b_node', 'length_ab', 'length_ba', 'direction']

            dict_field = {}
            for k in self.skims:
                a, b, t = self.skims[k]
                all_types.append(np.float64)
                all_types.append(np.float64)
                all_titles.append((k + '_ab').encode('ascii','ignore'))
                all_titles.append((k + '_ba').encode('ascii','ignore'))

                dict_field[k + '_ab'] = a
                if self.bidirectional:
                    dict_field[k + '_ba'] = b
                else:
                    dict_field[k + '_ba'] = -1

            dt = [(t, d) for t, d in zip(all_titles, all_types)]

            anode = self.netlayer.fieldNameIndex('A_Node')
            bnode = self.netlayer.fieldNameIndex('B_Node')
            data = []

            if self.selected_only:
                self.features = self.netlayer.selectedFeatures()
            else:
                self.features = self.netlayer.getFeatures()

            p = 0
            for feat in self.features:
                line = []
                line.append(feat.attributes()[self.linkid])
                line.append(feat.attributes()[anode])
                line.append(feat.attributes()[bnode])
                line.append(feat.attributes()[self.ablength])
                if self.bidirectional:
                    line.append(feat.attributes()[self.balength])
                    line.append(feat.attributes()[self.directionfield])
                else:
                    line.append(-1)
                    line.append(1)

                # We append the skims now
                for k in all_titles:
                    if k in dict_field:
                        if dict_field[k] >= 0:
                            line.append(feat.attributes()[dict_field[k]])
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
                del data

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

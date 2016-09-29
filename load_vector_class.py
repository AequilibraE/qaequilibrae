# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# Name:       TRIP DISTRIBUTION
# Purpose:    Applying a growth factor method
#
# Author:      Pedro Camargo
# Website:    www.AequilibraE.com
# Repository:
#
# Created:     12/01/2014
# Copyright:   (c) Pedro Camargo 2014
# Licence:     GPL
# -------------------------------------------------------------------------------

from qgis.core import *
import qgis
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys, os
import time

import numpy as np

from WorkerThread import WorkerThread

class LoadVector(WorkerThread):
    def __init__(self, parentThread, layer, idx):
        WorkerThread.__init__(self, parentThread)
        self.layer = layer
        self.idx = idx
        self.matrix = None
        self.error = None
        self.procedure = procedure

    def doWork(self):
        layer = self.layer
        idx = self.idx
        featcount = layer.featureCount()
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (featcount))

        idx1 = idx[0]
        idx2 = idx[1]
        # We read all the vectors and put in a list of lists
        vector = []
        P = 0
        for feat in layer.getFeatures():
            P += 1
            a = feat.attributes()[idx1]
            b = feat.attributes()[idx2]
            vector.append([a, b])
            if P % 100 == 0:
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(P)))

        vector = np.array(vector)  # transform the list of lists in NumPy array

        zones = np.max(vector[:, 0]) + 1
        vec = np.zeros(zones)
        vec[zones[:,0]] = zones[:,1]

        # self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (0))
        # P = 0
        # for i in vectors:
        #     vec[i[0].astype(int)] = i[1]
        #     P += 1
        #     if P % 100 == 0:
        #         self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(P)))

        self.vector = vec
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(featcount)))
        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), 'Vector loaded')
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

class LoadMatrix(WorkerThread):
    def __init__(self, parentThread, layer, idx, max_zone=None, filler=0):
        WorkerThread.__init__(self, parentThread)
        self.layer = layer
        self.idx = idx
        self.max_zone = max_zone
        self.matrix = None
        self.error = None
        self.filler = filler

    def doWork(self):
        layer = self.layer
        idx = self.idx
        max_zone = self.max_zone
        featcount = layer.featureCount()
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (featcount))

        error = None
        idx1 = idx[0]
        idx2 = idx[1]
        idx3 = idx[2]
        # We read all the vectors and put in a list of lists
        matrix = []
        P = 0
        for feat in layer.getFeatures():
            P += 1
            a = feat.attributes()[idx1]
            b = feat.attributes()[idx2]
            c = feat.attributes()[idx3]
            matrix.append([a, b, c])
            if P % 1000 == 0:
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(P)))
                self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),
                          ("Loading matrix: " + str(P) + "/" + str(featcount)))

        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (0))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), ("Converting Matrix to a NumPy array"))
        matrix = np.array(matrix)  # transform the list of lists in NumPy array

        if max_zone != np.max(matrix[:, 0:2]) + 1 and max_zone is not None:
            error = 'Vectors and matrix do not have matching dimensions'  # Compute number of zones in the problem
        mat = 0
        if max_zone is None:
            max_zone = np.max(matrix[:, 0:2]) + 1
        if error is None:
            mat = np.zeros((int(max_zone), int(max_zone)))
            mat.fill(self.filler)
            P = 0
            for i in matrix:
                mat[i[0].astype(int), i[1].astype(int)] = i[2]
                P += 1
                if P % 1000 == 0:
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(P)))
                    self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),
                              ("Converting matrix: " + str(P) + "/" + str(featcount)))

        self.matrix = mat
        self.error = error
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(featcount)))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), ("Matrix loading finalized"))
        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), 'LOADED-MATRIX')
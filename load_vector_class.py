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

from qgis.core import *
from PyQt4.QtCore import *
import numpy as np
from worker_thread import WorkerThread

class LoadVector(WorkerThread):
    def __init__(self, parentThread, layer, idx):
        WorkerThread.__init__(self, parentThread)
        self.layer = layer
        self.idx = idx
        self.matrix = None
        self.error = None

    def doWork(self):
        layer = self.layer
        idx = self.idx
        feat_count = layer.featureCount()
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (feat_count))

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
        if np.max(np.bincount(vector[:,0]))  > 1:
            self.error = 'Zone field is not unique'
        else:
            zones = np.max(vector[:, 0]) + 1
            vec = np.zeros(zones)
            vec[vector[:, 0].astype(int)] = vector[:, 1]

            self.vector = vec
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (int(feat_count)))
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), 'Vector loaded')
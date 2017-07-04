"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Creating impedance matrices
 Purpose:    Threaded procedure to compute impedance matrix

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
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

from multiprocessing.dummy import Pool as ThreadPool
import thread
from aequilibrae.paths import network_skimming, MultiThreadedNetworkSkimming
from ..common_tools import WorkerThread


def main():
    pass


class ComputeDistMatrix(WorkerThread):
    def __init__(self, parentThread, graph, result):
        WorkerThread.__init__(self, parentThread)
        self.graph = graph
        self.result = result
        self.skim_matrices = np.zeros((result.zones, result.zones, result.num_skims), np.float64)
        self.error = None
        self.report = []
        self.performed = 0

    def doWork(self):
        centroids = self.graph.centroids + 1

        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), 'Computing Impedance matrix')
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.graph.centroids)
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), 0)


        aux_res = MultiThreadedNetworkSkimming()
        aux_res.prepare(self.graph, self.result)

        pool = ThreadPool(self.result.cores)
        all_threads = {'count': 0}
        for O in range(self.result.zones):
            pool.apply_async(self.func_assig_thread, args=(O, self.graph, self.result, aux_res, all_threads, self.report))
        pool.close()
        pool.join()

        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), self.graph.centroids)

        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), "Saving Outputs")
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), None)

    def func_assig_thread(self, O, g, res, aux_res, all_threads, report):
        if thread.get_ident() in all_threads:
            th = all_threads[thread.get_ident()]
        else:
            all_threads[thread.get_ident()] = all_threads['count']
            th = all_threads['count']
            all_threads['count'] += 1
        a = network_skimming(O, g, res, aux_res, th)
        if a != O:
            report.append(a)

        self.performed += 1
        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), self.performed)
        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), str(self.performed) + ' / ' + str(self.matrix.shape[0] - 1))

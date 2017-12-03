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
from ..common_tools import WorkerThread

no_binary = False
try:
    from aequilibrae.paths import skimming_single_origin, MultiThreadedNetworkSkimming
except:
    no_binary = True
    
class ComputeDistMatrix(WorkerThread):
    def __init__(self, parentThread, graph, result):
        WorkerThread.__init__(self, parentThread)
        self.graph = graph
        self.result = result
        self.error = None
        self.report = []
        self.performed = 0

    def doWork(self):
        centroids = self.graph.centroids + 1

        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), 'Computing Impedance matrix_procedures')
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.graph.num_zones)
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), 0)

        aux_res = MultiThreadedNetworkSkimming()
        aux_res.prepare(self.graph, self.result)

        origins = list(self.graph.centroids)

        # catch errors
        if self.graph.cost_field is None:
            raise ValueError('The graph was not set for computation. Use graph.set_graph')
        if self.result.__graph_id__ is None:
            raise ValueError('The results object was not prepared. Use results.prepare(graph)')
        elif self.result.__graph_id__ != self.graph.__id__:
            raise ValueError('The results object was prepared for a different graph')
        else:
            pool = ThreadPool(self.result.cores)
            all_threads = {'count': 0}
            for O in origins:
                pool.apply_async(self.func_assig_thread, args=(O, aux_res, all_threads, self.report))
            pool.close()
            pool.join()

        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), self.graph.num_zones)
        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), "Saving Outputs")
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), None)

    def func_assig_thread(self, O, aux_res, all_threads, report):
        if thread.get_ident() in all_threads:
            th = all_threads[thread.get_ident()]
        else:
            all_threads[thread.get_ident()] = all_threads['count']
            th = all_threads['count']
            all_threads['count'] += 1
        a = skimming_single_origin(O, self.graph, self.result, aux_res, th)

        if a != O:
            report.append(a)

        self.performed += 1
        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), self.performed)
        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), str(self.performed) + ' / ' + str(self.matrix.shape[0] - 1))

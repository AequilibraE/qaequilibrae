"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Performing traffic assignment procedure
 Purpose:    Executes traffic assignment procedure in a separate thread

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    30/10/2016
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4.QtCore import *
from auxiliary_functions import *

from global_parameters import *
from worker_thread import WorkerThread
from multiprocessing.dummy import Pool as ThreadPool
from aequilibrae.paths import ota
import numpy as np
import thread

class TrafficAssignmentProcedure(WorkerThread):
    def __init__(self, parentThread, matrix, graph, results, method, skims=None, critical=None):
        WorkerThread.__init__(self, parentThread)

        self.matrix = matrix
        self.graph = graph
        self.results = results
        self.method = method
        self.skims = skims
        self.critical = critical
        self.error = None
        self.all_threads = {}
        self.performed = 0
        self.report = []

    def doWork(self):

        self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), self.matrix.shape[0])
        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), 0)

        # If we are going to perform All or Nothing
        if self.method['algorithm'] == 'AoN':
            pool = ThreadPool(self.results.cores)
            self.all_threads['count'] = 0

            for O in range(self.results.zones):
                a = self.matrix[O, :]
                if np.sum(a) > 0:
                    #self.func_assig_thread(O, a)
                    pool.apply_async(self.func_assig_thread, args=(O, a))
            pool.close()
            pool.join()

        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), "DONE")
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), None)

    def func_assig_thread(self, O, a):
        if thread.get_ident() in self.all_threads:
            th = self.all_threads[thread.get_ident()]
        else:
            self.all_threads[thread.get_ident()] = self.all_threads['count']
            th = self.all_threads['count']
            self.all_threads['count'] += 1
        ota(O, a, self.graph, self.results, th, True)

        self.performed += 1
        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), self.performed)
        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), str(self.performed) + ' / ' + str(self.matrix.shape[0]-1))

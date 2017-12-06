"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Performing traffic assignment procedure
 Purpose:    Executes traffic assignment procedure in a separate thread

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:   Pedro Camargo
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    30/10/2016
 Updated:    07/06/2017
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4.QtCore import *
from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *
from ..common_tools import WorkerThread
from multiprocessing.dummy import Pool as ThreadPool
import numpy as np
import thread

no_binary = False
try:
    from aequilibrae.paths import one_to_all, MultiThreadedAoN
except:
    no_binary = True

class TrafficAssignmentProcedure(WorkerThread):
    def __init__(self, parentThread, matrix, graph, results, method, skims=None, critical=None):
        WorkerThread.__init__(self, parentThread)

        self.matrix = matrix
        self.graph = graph
        self.results = results
        self.method = method
        self.skims = skims
        self.critical = critical
        self.all_threads = {}
        self.performed = 0
        self.report = []
        self.aux_res = MultiThreadedAoN()
        self.aux_res.prepare(graph, results)

    def doWork(self):

        self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), self.matrix.zones)
        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), 0)

        self.matrix.matrix_view = self.matrix.matrix_view.reshape((self.graph.num_zones, self.graph.num_zones,
                                                                   self.results.classes['number']))
        mat = self.matrix.matrix_view
        pool = ThreadPool(self.results.cores)
        self.all_threads = {'count': 0}
        for orig in self.matrix.index:
            i = self.graph.nodes_to_indices[orig]
            if np.nansum(mat[i, :, :]) > 0:
                if orig >= self.graph.nodes_to_indices.shape[0]:
                    self.report.append("Centroid " + str(orig) + " does not exist in the graph")
                elif self.graph.fs[int(orig)] == self.graph.fs[int(orig + 1)]:
                    self.report.append("Centroid " + str(orig) + " does not exist in the graph")
                else:
                    pool.apply_async(self.func_assig_thread, args=(orig))
                    # self.func_assig_thread(orig)
        pool.close()
        pool.join()

        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), self.matrix.zones)
        self.results.link_loads = np.sum(self.aux_res.temp_link_loads, axis=2)

        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), "Saving Outputs")
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), None)


    def func_assig_thread(self, O):
        if thread.get_ident() in self.all_threads:
            th = self.all_threads[thread.get_ident()]
        else:
            self.all_threads[thread.get_ident()] = self.all_threads['count']
            th = self.all_threads['count']
            self.all_threads['count'] += 1
        x = one_to_all(O, self.matrix, self.graph, self.results, self.aux_res, th)
        if x != O:
            self.report.append(x)



        self.performed += 1
        self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), self.performed)
        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), str(self.performed) + ' / ' + str(self.matrix.zones))

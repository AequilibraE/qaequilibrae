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
import aequilibrae as ae
from ..common_tools import WorkerThread


def main():
    pass


class ComputeDistMatrix(WorkerThread):
    def __init__(self, parentThread, graph, result):
        WorkerThread.__init__(self, parentThread)
        self.graph = graph
        self.result = result
        self.skim_matrices = np.zeros((result.zones, result.zones, result.num_skims), np.float64)
        #self.cores = cores
        self.error = None
        self.evol_bar = 0 #evol_bar

    def doWork(self):
        evol_bar = self.evol_bar
        centroids = self.graph.centroids+1
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Computing Impedance matrix'))
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, centroids-1))
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, 0))

        for origin in xrange(1, centroids):
            trash = ae.paths.path_computation(origin, 0, self.graph, self.result)
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, origin))
            for i, skm in enumerate(self.graph.skim_fields):
                self.skim_matrices[origin, :, i] = self.result.temporary_skims[:, i][0:centroids].copy()
            self.result.reset()

        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Computation Finalized. Writing results'))
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), 0)

    def func_assig(self, orig, graph_costs, b_nodes, graph_fs, idsgraph, graph_skim, no_path, skims, thread_dict,
                   predecessors, conn, temp_skims, evol_bar):

        ct = thread.get_ident()
        if ct in thread_dict.keys():
            ct = thread_dict[ct]
        else:
            a = len(thread_dict.keys())
            thread_dict[ct] = a
            ct = a

        a = AoN.SKIMS_One_to_all(orig, graph_costs, b_nodes, graph_fs, idsgraph, graph_skim, no_path[orig, :], skims[orig, :, :],
                                 predecessors[:, ct], conn[:, ct], temp_skims[:, :, ct])
        self.assigned[0] += 1

        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, str(self.assigned[0])))

if __name__ == '__main__':
    main()

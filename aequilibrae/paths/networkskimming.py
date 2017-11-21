"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Network skimming
 Purpose:    Implement skimming algorithms based on Cython's path finding and skimming

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camrgo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-07-03
 Updated:    2017-05-07
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """


import sys
sys.dont_write_bytecode = True

try:
    import qgis
    from qgis.core import *
    from PyQt4.QtCore import SIGNAL
except:
    pass

import numpy as np
from multiprocessing.dummy import Pool as ThreadPool
import thread

from multi_threaded_skimming import MultiThreadedNetworkSkimming
no_binaries = False
try:
    from AoN import skimming_single_origin
except:
    no_binaries = True

def main():
    pass


def network_skimming(graph, results, origins=None):
    aux_res = MultiThreadedNetworkSkimming()
    aux_res.prepare(graph, results)

    if origins is None:
        origins = list(graph.centroids)
    # catch errors
    if graph.cost_field is None:
        raise ValueError('The graph was not set for computation. Use graph.set_graph')
    if results.__graph_id__ is None:
        raise ValueError('The results object was not prepared. Use results.prepare(graph)')
    elif results.__graph_id__ != graph.__id__:
        raise ValueError('The results object was prepared for a different graph')
    else:
        pool = ThreadPool(results.cores)
        all_threads = {'count': 0}
        report = []
        for O in origins:
            pool.apply_async(func_assig_thread, args=(O, graph, results, aux_res, all_threads, report))
        pool.close()
        pool.join()
    return report


def func_assig_thread(O, g, res, aux_res, all_threads, report):
    if thread.get_ident() in all_threads:
        th = all_threads[thread.get_ident()]
    else:
        all_threads[thread.get_ident()] = all_threads['count']
        th = all_threads['count']
        all_threads['count'] += 1
    a = skimming_single_origin(O, g, res, aux_res, th)

    if a != O:
        report.append(a)


if __name__ == '__main__':
    main()

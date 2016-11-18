"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Traffic assignment
 Purpose:    Implement ttaffic assignment algorithms based on Cython's network loading procedures

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camrgo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    15/09/2013
 Updated:    30/09/2016
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
import platform
from multiprocessing.dummy import Pool as ThreadPool
import thread

plat = platform.system()
if plat == 'Windows':
    import struct
    if (8 * struct.calcsize("P")) == 64:
        from win64 import *
    if (8 * struct.calcsize("P")) == 32:
        from win32 import *
if plat == 'Linux':
    import struct
    if (8 * struct.calcsize("P")) == 64:
        from linux64 import *
if plat == 'Darwin':
    from mac import *

def main():
    pass


def all_or_nothing(matrix, graph, results):

    # catch errors
    if results.__graph_id__ is None:
        raise ValueError('The results object was not prepared. Use results.prepare(graph)')

    elif results.__graph_id__ != graph.__id__:
        raise ValueError('The results object was prepared for a different graph')
    else:
        pool = ThreadPool(results.cores)
        all_threads = {'count': 0}
        for O in range(results.zones):
            a = matrix[O, :]
            if np.sum(a) > 0:
                pool.apply_async(func_assig_thread, args=(O, a, graph, results, all_threads))
        pool.close()
        pool.join()


def func_assig_thread(O, a, g, res, all_threads):
    if thread.get_ident() in all_threads:
        th = all_threads[thread.get_ident()]
    else:
        all_threads[thread.get_ident()] = all_threads['count']
        th = all_threads['count']
        all_threads['count'] += 1

    one_to_all(O, a, g, res, th, True)


def ota(O, a, g, res, th, b):
    one_to_all(O, a, g, res, th, b)

if __name__ == '__main__':
    main()

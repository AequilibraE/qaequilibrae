"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Iterative proportinal fitting
 Purpose:    Applies proportinal fitting in a separate thread

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-09-29
 Updated:    2016-10-03
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4.QtCore import *
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

from worker_thread import WorkerThread
from aequilibrae.distribution import Ipf

class IpfProcedure(WorkerThread):
    def __init__(self, parentThread, seed, rows, columns):
        WorkerThread.__init__(self, parentThread)
        self.ipf = Ipf(seed, rows, columns)
        self.error = None

    def doWork(self):
        self.ipf.fit()
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),0)

if __name__ == '__main__':
    main()

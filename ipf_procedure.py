# -------------------------------------------------------------------------------
# Name:       TRAFFIC ASSIGNMENT
# Purpose:    Implement procedures to translate a layer and parameters into entry for assignment
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
from PyQt4.QtCore import *
import sys
sys.path.append("C:/Users/Pedro/.qgis2/python/plugins/AequilibraE/")

from WorkerThread import WorkerThread
from aequilibrae.distribution import Ipf

class IpfProcedure(WorkerThread):
    def __init__(self, parentThread, seed, rows, columns):
        WorkerThread.__init__(self, parentThread)
        self.ipf = Ipf(seed, rows, columns)
        self.error = None

    def doWork(self):
        self.ipf.fit()
        #self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Computation Finalized. Writing results'))
        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"),0)

if __name__ == '__main__':
    main()

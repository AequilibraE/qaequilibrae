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
from PyQt4.QtCore import *
import sys
import os

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

from ..common_tools import WorkerThread
from ..aequilibrae.aequilibrae.distribution import Ipf


class IpfProcedure(WorkerThread):
    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.ipf = Ipf(**kwargs)
        self.report = None

    def doWork(self):
        self.ipf.fit()
        self.report = self.ipf.report
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),0)
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),0)

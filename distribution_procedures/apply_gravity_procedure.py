"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Applying Gravity model
 Purpose:    Applies synthetic gravity model

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-10-03
 Updated:    2017-10-10
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from PyQt4.QtCore import *
import sys
import os
from ..common_tools import WorkerThread
from aequilibrae.distribution import GravityApplication


class ApplyGravityProcedure(WorkerThread):
    def __init__(self, parentThread,  **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.gravity = GravityApplication(**kwargs)
        self.error = None

    def doWork(self):
        self.gravity.apply()
        self.report = self.gravity.report
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), 0)

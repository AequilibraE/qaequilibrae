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
 Updated:    2018-12-27
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
import qgis
from qgis.PyQt.QtCore import *
from aequilibrae.distribution import Ipf
from ..common_tools import WorkerThread


class IpfProcedure(WorkerThread):

    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.ipf = Ipf(**kwargs)
        self.error = None
        self.report = []

    def doWork(self):
        try:
            self.ipf.fit()
            self.report = self.ipf.report
        except ValueError as e:
            self.error = e
        self.finished_threaded_procedure.emit(0)

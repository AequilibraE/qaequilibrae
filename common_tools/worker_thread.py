"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Worker thread
 Purpose:    Implements worker thread

 Original Author:  UNKNOWN. COPIED FROM STACKOVERFLOW BUT CAN'T REMEMBER EXACTLY WHERE
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

from qgis.core import *
from qgis.PyQt.QtCore import *


class WorkerThread(QThread):
    jobFinished = pyqtSignal("PyQt_PyObject")
    ProgressValue = pyqtSignal("PyQt_PyObject")
    ProgressMaxValue = pyqtSignal("PyQt_PyObject")
    ProgressText = pyqtSignal("PyQt_PyObject")
    finished_threaded_procedure = pyqtSignal("PyQt_PyObject")

    # For the desire lines procedure
    desire_lines = pyqtSignal("PyQt_PyObject")

    # for using the assignment procedure
    assignment = pyqtSignal("PyQt_PyObject")

    def __init__(self, parentThread):
        QThread.__init__(self, parentThread)

    def run(self):
        self.running = True
        success = self.doWork()
        self.jobFinished.emit(success)

    def stop(self):
        self.running = False
        pass

    def doWork(self):
        return True

    def cleanUp(self):
        pass

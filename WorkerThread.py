from qgis.core import *
from PyQt4.QtCore import *

class WorkerThread(QThread):
    def __init__(self, parentThread):
        QThread.__init__(self, parentThread)
    def run(self):
        self.running = True
        success = self.doWork()
        self.emit(SIGNAL("jobFinished(PyQt_PyObject)"), success)
    def stop(self):
        self.running = False
        pass
    def doWork(self):
        return True
    def cleanUp(self):
        pass
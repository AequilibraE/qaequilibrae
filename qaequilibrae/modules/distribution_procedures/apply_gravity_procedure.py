from qgis.PyQt.QtCore import pyqtSignal
from aequilibrae.distribution import GravityApplication
from aequilibrae.utils.interface.worker_thread import WorkerThread


class ApplyGravityProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.gravity = GravityApplication(**kwargs)
        self.error = None
        self.output = None
        self.report = []

    def doWork(self):
        self.gravity.apply()
        self.output = self.gravity.output
        self.report = self.gravity.report
        self.signal.emit(["finished"])

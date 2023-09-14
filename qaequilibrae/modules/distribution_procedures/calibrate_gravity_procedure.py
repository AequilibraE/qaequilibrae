from aequilibrae.distribution import GravityCalibration
from aequilibrae.utils.worker_thread import WorkerThread
from qgis.PyQt.QtCore import *


class CalibrateGravityProcedure(WorkerThread):
    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.gravity = GravityCalibration(**kwargs)
        self.error = None
        self.report = []
        self.model = None

    def doWork(self):
        self.gravity.calibrate()
        self.report = self.gravity.report
        self.model = self.gravity.model
        self.jobFinished.emit("calibrate")

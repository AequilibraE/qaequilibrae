from qgis.PyQt.QtCore import *

from aequilibrae.utils.worker_thread import WorkerThread

class CalibrateGravityProcedure(WorkerThread):
    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.gravity = GravityCalibration(**kwargs)
        self.error = None
        self.report = []
        self.model = None

    def doWork(self):
        try:
            self.gravity.calibrate()
            self.report = self.gravity.report
            self.model = self.gravity.model
        except ValueError as e:
            self.error = e
        self.finished_threaded_procedure.emit("calibrate")

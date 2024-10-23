from aequilibrae.distribution import GravityCalibration
from aequilibrae.utils.interface.worker_thread import WorkerThread


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
        self.jobFinished.emit(["finished", 0, 0, "calibrate", "master"])

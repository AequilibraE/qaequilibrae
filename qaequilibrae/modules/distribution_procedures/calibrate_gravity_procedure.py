from aequilibrae.distribution import GravityCalibration
from PyQt5.QtCore import QObject
from qgis.PyQt.QtCore import *


class CalibrateGravityProcedure(QObject):
    def __init__(self, parentThread, **kwargs):
        QObject.__init__(self, parentThread)
        self.gravity = GravityCalibration(**kwargs)
        self.error = None
        self.report = []
        self.model = None

    def doWork(self):
        self.gravity.calibrate()
        self.report = self.gravity.report
        self.model = self.gravity.model
        # self.jobFinished.emit("calibrate")

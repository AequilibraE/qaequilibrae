from aequilibrae.distribution import GravityApplication
from PyQt5.QtCore import QObject
from qgis.PyQt.QtCore import *


class ApplyGravityProcedure(QObject):
    def __init__(self, parentThread, **kwargs):
        QObject.__init__(self, parentThread)
        self.gravity = GravityApplication(**kwargs)
        self.error = None
        self.output = None
        self.report = []

    def doWork(self):
        self.gravity.apply()
        self.output = self.gravity.output
        self.report = self.gravity.report
        # self.gravity.finished.emit("apply_gravity")

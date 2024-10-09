from aequilibrae.distribution import Ipf

from PyQt5.QtCore import QObject


class IpfProcedure(QObject):
    def __init__(self, parentThread, **kwargs):
        QObject.__init__(self, parentThread)
        self.ipf = Ipf(**kwargs)
        self.error = None
        self.output = None
        self.report = []

    def doWork(self):
        self.ipf.fit()
        self.report = self.ipf.report
        self.output = self.ipf.output
        # self.jobFinished.emit("finishedIPF")

from PyQt5.QtCore import pyqtSignal
from aequilibrae.distribution import Ipf

from ..common_tools import WorkerThread


class IpfProcedure(WorkerThread):
    finished_threaded_procedure = pyqtSignal(object)

    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.ipf = Ipf(**kwargs)
        self.error = None
        self.output = None
        self.report = []

    def doWork(self):
        try:
            self.ipf.fit()
            self.report = self.ipf.report
            self.output = self.ipf.output
        except ValueError as e:
            self.error = e
        self.finished_threaded_procedure.emit('finishedIPF')

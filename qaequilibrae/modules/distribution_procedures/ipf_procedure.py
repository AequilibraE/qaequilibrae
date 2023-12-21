from aequilibrae.distribution import Ipf

from aequilibrae.utils.worker_thread import WorkerThread


class IpfProcedure(WorkerThread):
    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.ipf = Ipf(**kwargs)
        self.error = None
        self.output = None
        self.report = []

    def doWork(self):
        self.ipf.fit()
        self.report = self.ipf.report
        self.output = self.ipf.output
        self.jobFinished.emit("finishedIPF")

from qgis.PyQt.QtCore import pyqtSignal

from aequilibrae.utils.interface.worker_thread import WorkerThread
from qaequilibrae.modules.transit_procedures.transit_assignment_runner import run_transit_assignment


class TransitAssignProcedure(WorkerThread):
    """Run transit assignment in the dialog's worker thread."""

    signal = pyqtSignal(object)

    def __init__(self, parentThread, project, transit_data, configs, action):
        super().__init__(parentThread)
        self.project = project
        self.transit_data = transit_data
        self.configs = configs
        self.action = action

    def doWork(self):
        def report(step, maximum, text):
            if step == 1:
                self.signal.emit(["start", maximum, text])
            else:
                self.signal.emit(["update", step, text])

        try:
            run_transit_assignment(
                self.project,
                self.transit_data,
                self.configs,
                self.action,
                progress=report,
            )
            return True
        finally:
            self.signal.emit(["finished"])

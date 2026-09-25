"""Worker for the dialog's interactive, single-OD route inspection.

Assignment and choice-set building use the registered RouteChoice Processing
algorithm instead. This worker only dispatches the interactive operation and
notifies the dialog so it can plot the returned routes.
"""

from qgis.PyQt.QtCore import pyqtSignal
from aequilibrae.utils.interface.worker_thread import WorkerThread

from qaequilibrae.modules.processing_provider.paths_procedures.route_choice import run_single_route_choice


class RouteChoiceProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, aeq_project, parameters):
        WorkerThread.__init__(self, parentThread)
        self.project = aeq_project
        self.parameters = parameters
        self.graph = None
        self.rc = None

    def doWork(self):
        self.rc, self.graph = run_single_route_choice(
            self.project,
            self.parameters["configuration"],
            self.parameters["node_from"],
            self.parameters["node_to"],
            self.parameters["matrix"],
        )
        self.signal.emit(["finished"])

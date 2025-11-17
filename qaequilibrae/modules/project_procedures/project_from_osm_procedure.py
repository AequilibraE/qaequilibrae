from aequilibrae.utils.interface.worker_thread import WorkerThread
from qgis.PyQt.QtCore import pyqtSignal
from shapely.geometry import box


class ProjectFromOSMProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, qgis_project, bbox) -> None:
        WorkerThread.__init__(self, parentThread)
        self.qgis_project = qgis_project
        self.bbox = bbox

    def doWork(self):
        self.qgis_project.project.network.signal = self.signal
        self.qgis_project.project.network.create_from_osm(box(*self.bbox))

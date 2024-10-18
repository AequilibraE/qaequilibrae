import shapely.wkb

from aequilibrae.utils.interface.worker_thread import WorkerThread
from PyQt5.QtCore import pyqtSignal


class AddZonesProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, project, area_layer, select_only, add_centroids, field_correspondence):
        WorkerThread.__init__(self, parentThread)
        self.project = project
        self.lyr = area_layer
        self.select_only = select_only
        self.field_corresp = field_correspondence
        self.add_centroids = add_centroids

    def doWork(self):
        features = list(self.lyr.selectedFeatures()) if self.select_only else list(self.lyr.getFeatures())

        self.signal.emit(["start", 0, len(features), self.tr("Importing zones"), "master"])

        idx_id = self.field_corresp["zone_id"]
        zoning = self.project.zoning
        for i, feat in enumerate(features):
            zone = zoning.new(feat.attributes()[idx_id])
            zone.geometry = shapely.wkb.loads(feat.geometry().asWkb().data())
            for field, idx in self.field_corresp.items():
                if idx == idx_id:
                    continue
                zone.__dict__[field] = feat.attributes()[idx]
            zone.save()
            if self.add_centroids:
                zone.add_centroid(None)
            self.signal.emit(["update", 0, i + 1, f"Num. zones: {i}", "master"])
        self.signal.emit(["finished"])

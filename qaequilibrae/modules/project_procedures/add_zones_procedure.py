import shapely.wkb

from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal


class AddZonesProcedure(QObject):
    ProgressValue = pyqtSignal(object)
    ProgressText = pyqtSignal(object)
    ProgressMaxValue = pyqtSignal(object)
    finished = pyqtSignal(object)

    def __init__(self, parentThread, project, area_layer, select_only, add_centroids, field_correspondence):
        QObject.__init__(self, parentThread)
        self.project = project
        self.lyr = area_layer
        self.select_only = select_only
        self.field_corresp = field_correspondence
        self.add_centroids = add_centroids

    def doWork(self):
        features = list(self.lyr.selectedFeatures()) if self.select_only else list(self.lyr.getFeatures())
        self.emit_messages(message=self.tr("Importing zones"), value=0, max_val=len(features))

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
            self.emit_messages(value=i + 1)
        self.finished.emit("DONE")

    def emit_messages(self, message="", value=-1, max_val=-1):
        if len(message) > 0:
            self.ProgressText.emit(message)
        if value >= 0:
            self.ProgressValue.emit(value)
        if max_val >= 0:
            self.ProgressMaxValue.emit(max_val)

import shapely.wkb
from shapely.geometry import Point

from aequilibrae.utils.worker_thread import WorkerThread
from PyQt5.QtCore import pyqtSignal


class AddsConnectorsProcedure(WorkerThread):
    ProgressValue = pyqtSignal(object)
    ProgressText = pyqtSignal(object)
    ProgressMaxValue = pyqtSignal(object)
    finished_threaded_procedure = pyqtSignal(object)

    def __init__(
        self, parentThread, qgis_project, link_types, modes, num_connectors, source, radius=None, layer=None, field=None
    ):
        WorkerThread.__init__(self, parentThread)
        self.qgis_project = qgis_project
        self.project = qgis_project.project
        self.link_types = link_types
        self.radius = radius
        self.modes = modes
        self.num_connectors = num_connectors
        self.source = source
        self.layer = layer
        self.field = field

    def doWork(self):
        if self.source == "zone":
            self.do_from_zones()
        elif self.source == "network":
            self.do_from_network()
        else:
            self.do_from_layer()

        self.ProgressText.emit("DONE")

    def do_from_zones(self):
        zoning = self.project.zoning
        zoning.refresh_connection()
        tot_zones = [x[0] for x in zoning.conn.execute("select count(*) from zones")][0]
        self.ProgressMaxValue.emit(tot_zones)

        zones = [x[0] for x in zoning.conn.execute("select zone_id from zones")]
        for counter, zone_id in enumerate(zones):
            zone = zoning.get(zone_id)
            zone.conn = zoning.conn
            zone.add_centroid(None)
            for mode_id in self.modes:
                zone.connect_mode(mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.ProgressValue.emit(counter + 1)

    def do_from_network(self):
        nodes = self.project.network.nodes
        nodes.refresh()
        nodes.refresh_connection()
        self.project.network.refresh_connection()
        self.ProgressMaxValue.emit(self.project.network.count_centroids())
        centroids = [x[0] for x in nodes.conn.execute("select node_id from nodes where is_centroid=1")]
        for counter, zone_id in enumerate(centroids):
            print(zone_id)
            node = nodes.get(zone_id)
            geo = self.polygon_from_radius(node.geometry)
            for mode_id in self.modes:
                node.connect_mode(area=geo, mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.ProgressValue.emit(counter + 1)

    def do_from_layer(self):
        fields = self.layer.fields()
        idx = fields.indexOf(self.field.name())
        features = list(self.layer.getFeatures())
        self.ProgressMaxValue.emit(len(features))

        nodes = self.project.network.nodes
        nodes.refresh_connection()
        for counter, feat in enumerate(features):
            zone_id = feat.attributes()[idx]
            node = nodes.new_centroid(zone_id)
            node.geometry = shapely.wkb.loads(feat.geometry().asWkb().data())
            node.save()
            geo = self.polygon_from_radius(node.geometry)
            for mode_id in self.modes:
                node.connect_mode(area=geo, mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.ProgressValue.emit(counter + 1)

    def polygon_from_radius(self, point: Point):
        # We approximate with the radius of the Earth at the equator
        return point.buffer(self.radius / 110000)

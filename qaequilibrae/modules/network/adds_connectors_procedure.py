import shapely.wkb
from shapely.geometry import Point

from aequilibrae.project.database_connection import database_connection
from aequilibrae.utils.db_utils import commit_and_close
from aequilibrae.utils.interface.worker_thread import WorkerThread
from PyQt5.QtCore import pyqtSignal


class AddsConnectorsProcedure(WorkerThread):
    signal = pyqtSignal(object)

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

        self.signal.emit(["finished"])

    def do_from_zones(self):
        zoning = self.project.zoning

        with commit_and_close(database_connection("network")) as conn:
            tot_zones = [x[0] for x in conn.execute("select count(*) from zones")][0]

            zones = [x[0] for x in conn.execute("select zone_id from zones")]

        self.signal.emit(["start", 0, tot_zones, "Adding connectors from zones", "master"])
        for counter, zone_id in enumerate(zones):
            zone = zoning.get(zone_id)
            zone.add_centroid(None)
            for mode_id in self.modes:
                zone.connect_mode(mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.signal.emit(["update", 0, counter + 1, f"Connector from zone: {zone_id}", "master"])

    def do_from_network(self):
        nodes = self.project.network.nodes
        nodes.refresh()

        with commit_and_close(database_connection("network")) as conn:
            centroids = [x[0] for x in conn.execute("select node_id from nodes where is_centroid=1")]

        self.signal.emit(["start", 0, self.project.network.count_centroids(), "Adding connectors from nodes", "master"])
        for counter, zone_id in enumerate(centroids):
            node = nodes.get(zone_id)
            geo = self.polygon_from_radius(node.geometry)
            for mode_id in self.modes:
                node.connect_mode(area=geo, mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.signal.emit(["update", 0, counter + 1, f"Connector from node: {zone_id}", "master"])

    def do_from_layer(self):
        nodes = self.project.network.nodes
        nodes.refresh()

        idx = self.layer.fields().indexOf(self.field)
        features = list(self.layer.getFeatures())

        self.signal.emit(["start", 0, self.project.network.count_centroids(), "Adding connectors from layer", "master"])
        for counter, feat in enumerate(features):
            zone_id = feat.attributes()[idx]
            node = nodes.new_centroid(zone_id)
            node.geometry = shapely.wkb.loads(feat.geometry().asWkb().data())
            node.save()
            geo = self.polygon_from_radius(node.geometry)
            for mode_id in self.modes:
                node.connect_mode(area=geo, mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.signal.emit(["update", 0, counter + 1, f"Connector from layer feature: {zone_id}", "master"])

    def polygon_from_radius(self, point: Point):
        # We approximate with the radius of the Earth at the equator
        return point.buffer(self.radius / 110000)

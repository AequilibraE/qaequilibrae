from aequilibrae.utils.interface.worker_thread import WorkerThread
from qgis.PyQt.QtCore import pyqtSignal
import shapely.wkb

from qaequilibrae.modules.common_tools import polygon_from_radius


class AddsConnectorsProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(
        self,
        parentThread,
        qgis_project,
        link_types,
        modes,
        num_connectors,
        source,
        limit_to_zone=True,
        radius=None,
        layer=None,
        field=None,
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
        self.limit_to_zone = limit_to_zone

    def doWork(self):
        if self.source == "zone":
            self.do_from_zones()
        elif self.source == "network":
            self.do_from_network()
        else:
            self.do_from_layer()

        self.project.network.nodes.refresh()
        self.project.network.links.refresh()
        self.signal.emit(["finished"])

    def do_from_zones(self):
        zoning = self.project.zoning

        self.signal.emit(["start", len(zoning.all_zones()), "Adding connectors from zones"])
        for idx, (zone_id, zone) in enumerate(zoning.all_zones().items()):
            zone.add_centroid(None)
            for mode_id in self.modes:
                zone.connect_mode(
                    mode_id=mode_id,
                    link_types=self.link_types,
                    connectors=self.num_connectors,
                    limit_to_zone=self.limit_to_zone,
                )
            self.signal.emit(["update", idx + 1, f"Connector from zone: {zone_id}"])

    def do_from_network(self):
        nodes = self.project.network.nodes
        nodes.refresh()

        centroids = nodes.data[nodes.data["is_centroid"] == 1].node_id.tolist()

        self.signal.emit(["start", self.project.network.count_centroids(), "Adding connectors from nodes"])
        for counter, zone_id in enumerate(centroids):
            node = nodes.get(zone_id)
            geo = polygon_from_radius(node.geometry, self.radius)
            for mode_id in self.modes:
                node.connect_mode(area=geo, mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.signal.emit(["update", counter + 1, f"Connector from node: {zone_id}"])

    def do_from_layer(self):
        nodes = self.project.network.nodes
        nodes.refresh()

        self.signal.emit(["start", self.layer.featureCount(), "Adding connectors from layer"])
        for counter, feat in enumerate(self.layer.getFeatures()):
            node = nodes.new_centroid(feat.id())
            node.geometry = shapely.wkb.loads(feat.geometry().asWkb().data())
            node.save()
            geo = polygon_from_radius(node.geometry, self.radius)
            for mode_id in self.modes:
                node.connect_mode(area=geo, mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.signal.emit(["update", counter + 1, f"Connector from layer feature: {feat.id()}"])

"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Adding centroid connectors procedure
 Purpose:    Executes centroid addition procedure in a separate thread

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    30/01/2020
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from typing import List
from qgis.core import *
from qgis.PyQt.QtCore import *
from ..common_tools.auxiliary_functions import *
from sqlite3 import Connection as sqlc
import qgis
import numpy as np
from shapely.geometry import Point
import shapely.wkb

from ..common_tools.global_parameters import *
from ..common_tools import WorkerThread


class AddsConnectorsProcedure(WorkerThread):
    def __init__(self, parentThread, qgis_project, link_types, modes, radius, num_connectors, source, layer=None,
                 field=None):
        WorkerThread.__init__(self, parentThread)

    self.qgis_project = qgis_project
    self.project = qgis_project.project
    self.conn = self.project.conn
    self.link_types = link_types
    self.radius = radius
    self.modes = modes
    self.num_connectors = num_connectors
    self.source = source
    self.layer = layer
    self.field = field

    def doWork(self):

        if self.source == 'zone':
            self.do_from_zones()
        elif self.source == 'network':
            self.do_from_network()
        else:
            self.do_from_layer()

        self.ProgressText.emit("DONE")

    def do_from_zones(self):
        zoning = self.project.zoning
        tot_zones = [x[0] for x in self.conn.execute('select count(*) from zones')][0]
        self.ProgressMaxValue.emit(tot_zones)

        for counter, (zone_id, zone) in enumerate(zoning.all_zones()):
            zone.add_centroid(None)
            for mode_id in self.modes:
                zone.connect_mode(mode_id=mode_id, link_types=self.link_types, connectors=self.num_connectors)
            self.ProgressValue.emit(counter + 1)

    def do_from_network(self):
        nodes = self.project.network.nodes
        self.ProgressMaxValue.emit(self.project.network.count_centroids())

        centroids = [x[0] for x in self.conn.execute('select node_id from nodes where is_centroid=1')]
        for counter, zone_id in enumerate(centroids):
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

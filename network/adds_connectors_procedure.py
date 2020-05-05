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

from ..common_tools.global_parameters import *
from ..common_tools import WorkerThread


class AddsConnectorsProcedure(WorkerThread):
    def __init__(
            self,
            parentThread,
            project: str,
            centroid_layer_name: str,
            centroids_ids: str,
            max_length: int,
            max_connectors: int,
            allowed_link_types: List[str],
    ):
        WorkerThread.__init__(self, parentThread)
        self.conn = project
        self.centroid_layer_name = centroid_layer_name
        self.centroids_ids = centroids_ids
        self.max_length = max_length
        self.max_connectors = max_connectors
        self.allowed_link_types = allowed_link_types
        self.error = None
        self.insert_qry = """INSERT INTO links (direction, modes, link_type, geometry) 
                             VALUES({}, GeomFromText("{}", 4326))"""

    def doWork(self):
        self.conn = qgis.utils.spatialite_connect(self.conn)
        cursor = self.conn.cursor()

        # Checking with the centroid IDs overlap with Node IDs
        self.ProgressText.emit("Checking uniqueness of IDs")
        cursor.execute('SELECT node_id from nodes')
        node_ids = cursor.fetchall()
        node_ids = np.array(node_ids)
        node_ids=node_ids[:,0]
        centroids = get_vector_layer_by_name(self.centroid_layer_name)

        # Now we start to set the field for writing the new data
        idx2 = centroids.dataProvider().fieldNameIndex(self.centroids_ids)

        featcount = centroids.featureCount()
        self.ProgressMaxValue.emit(featcount)
        self.ProgressValue.emit(0)

        centroid_list = []
        for counter, feat in enumerate(centroids.getFeatures()):
            centroid_id = feat.attributes()[idx2]
            self.ProgressValue.emit(int(counter))
            centroid_list.append(centroid_id)
        centroid_list = np.array(centroid_list)

        if centroid_list.shape[0] > np.unique(centroid_list).shape[0]:
            self.error = 'Centroid IDs are not unique'
            self.ProgressText.emit("DONE")
            return

        intersect = np.intersect1d(centroid_list, node_ids)

        if intersect.shape[0] > 0:
            self.error = 'Centroid IDs overlap node IDs'
            self.ProgressText.emit("DONE")
            return

        cursor.execute("select mode_id from modes;")
        modes = cursor.fetchall()
        modes = [x[0] for x in modes]

        # TODO: Create a negative for the case only a few are selected to be excluded?
        link_types = ''
        if self.allowed_link_types:
            link_types = ['links.link_type ="{}"'.format(x) for x in self.allowed_link_types]
            link_types = ' AND ({}) '.format(' OR '.join(link_types))

        # The missing pieces in this query are: centroid's longitude, centroid's latitude, selection of link
        # types acceptable to have connectors linked AND the number of connectors we are interested in
        sql = """SELECT distinct node_id, AsWKT(nodes.geometry), links.modes, GLength(makeline(nodes.geometry,  
                 GeomFromText("Point ({long} {lat})", 4326)))
                 as distance FROM nodes
                 INNER JOIN links on links.a_node = nodes.node_id
                 where nodes.ROWID in 
                 (SELECT ROWID FROM SpatialIndex WHERE f_table_name = 'nodes' AND
                      search_frame = Buffer(GeomFromText("Point ({long} {lat})", 4326), {circle}))
                 {link_types}  
                 UNION 
                 SELECT distinct node_id, AsWKT(nodes.geometry), links.modes, GLength(makeline(nodes.geometry,  
                 GeomFromText("Point ({long} {lat})", 4326)))
                 as distance FROM nodes
                 INNER JOIN links on links.b_node = nodes.node_id
                 where nodes.ROWID in 
                 (SELECT ROWID FROM SpatialIndex WHERE f_table_name = 'nodes' AND
                       search_frame = Buffer(GeomFromText("Point ({long} {lat})", 4326), {circle}))
                 {link_types}  
                 ORDER BY distance
                 limit {connectors}"""

        missing_mode_sql = """SELECT distinct node_id, AsWKT(nodes.geometry), links.modes, 
                              GLength(makeline(nodes.geometry, GeomFromText("Point ({long} {lat})", 4326)))
                              as distance FROM nodes
                              INNER JOIN links on links.a_node = nodes.node_id
                              where nodes.ROWID in 
                              (SELECT ROWID FROM SpatialIndex WHERE f_table_name = 'nodes' AND
                                   search_frame = Buffer(GeomFromText("Point ({long} {lat})", 4326), {circle}))
                              AND instr(modes, "{srch_mode}") > 0 
                              {link_types}  
                              UNION 
                              SELECT distinct node_id, AsWKT(nodes.geometry), links.modes,
                              GLength(makeline(nodes.geometry, GeomFromText("Point ({long} {lat})", 4326)))
                              as distance FROM nodes
                              INNER JOIN links on links.b_node = nodes.node_id
                              where nodes.ROWID in 
                              (SELECT ROWID FROM SpatialIndex WHERE f_table_name = 'nodes' AND
                                    search_frame = Buffer(GeomFromText("Point ({long} {lat})", 4326), {circle}))
                              AND instr(modes, "{srch_mode}") > 0 
                              {link_types}  
                              ORDER BY distance
                              limit 1"""

        node_sql = """update nodes set node_id={nodeid}, is_centroid=1
                      where nodes.ROWID in
                      (SELECT ROWID FROM SpatialIndex WHERE f_table_name = 'nodes' AND
                      search_frame = GeomFromText("Point ({lon} {lat})", 4326))"""

        self.ProgressValue.emit(0)
        self.ProgressText.emit("Creating centroid connectors")

        for counter, feat in enumerate(centroids.getFeatures()):
            circle = 0.001
            centroid_id = feat.attributes()[idx2]
            self.ProgressValue.emit(int(counter))

            lon, lat = feat.geometry().asPoint()

            avail_nodes = 0
            attempts = 0
            while avail_nodes < self.max_connectors:
                qry = sql.format(long=lon, lat=lat, circle=circle, link_types=link_types,
                                 connectors=self.max_connectors)
                cursor.execute(qry)
                nodes = cursor.fetchall()
                node_ids = list(set([x[0] for x in nodes]))
                avail_nodes = len(node_ids)
                circle *= 2
                attempts += 1
                if attempts > 14:
                    break
            # Mode specific
            modes_found = ''.join([x[2] for x in nodes])
            missing_modes = [x for x in modes if x not in modes_found]
            mode_specific = {}
            if missing_modes:
                for m in missing_modes:
                    circle = 0.002
                    for attempts in range(20):
                        qry = missing_mode_sql.format(long=lon, lat=lat, circle=circle, link_types=link_types,
                                                      srch_mode=m)
                        cursor.execute(qry)
                        x = cursor.fetchall()
                        if x:
                            mode_specific[m] = x[0]
                            break
                        circle *= 2

            modes_for_nodes = {x[0]: '' for x in nodes}
            for node in nodes:
                modes_for_nodes[node[0]] += "".join(set(node[2]))

            for i, node in enumerate(nodes):
                geometry = "LINESTRING ({} {}, {})".format(lon, lat, node[1][6:-1])
                attributes = ", ".join(['0', "'{}'".format(modes_for_nodes[node[0]]), "'connector'"])
                qry = self.insert_qry.format(attributes, geometry)
                cursor.execute(qry)
                print(qry)
                qry = node_sql.format(nodeid=centroid_id, lon=lon, lat=lat)
                cursor.execute(qry)
                print(qry)
        self.conn.commit()
        self.ProgressText.emit("DONE")

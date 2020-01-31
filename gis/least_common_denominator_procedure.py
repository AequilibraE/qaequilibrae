"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Least commmon denominator
 Purpose:    Computes least common denominator between two polygon layers in a separate thread

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-09-26
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
# from PyQt4.QtCore import QVariant, SIGNAL
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsCoordinateTransform,
    QgsSpatialIndex,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsVectorLayer,
    QgsProject,
)
import copy

from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *
from ..common_tools.worker_thread import WorkerThread


class LeastCommonDenominatorProcedure(WorkerThread):
    def __init__(self, parentThread, flayer, tlayer, ffield, tfield):
        WorkerThread.__init__(self, parentThread)
        self.flayer = flayer
        self.tlayer = tlayer
        self.ffield = ffield
        self.tfield = tfield
        self.error = None
        self.result = None
        self.output_type = None
        self.transform = None
        self.poly_types = poly_types + multi_poly
        self.line_types = line_types + multi_line
        self.point_types = point_types + multi_point

    def doWork(self):
        flayer = self.flayer
        tlayer = self.tlayer
        ffield = self.ffield
        tfield = self.tfield

        self.from_layer = get_vector_layer_by_name(flayer)
        self.to_layer = get_vector_layer_by_name(tlayer)

        EPSG1 = QgsCoordinateReferenceSystem(int(self.from_layer.crs().authid().split(":")[1]))
        EPSG2 = QgsCoordinateReferenceSystem(int(self.to_layer.crs().authid().split(":")[1]))
        if EPSG1 != EPSG2:
            self.transform = QgsCoordinateTransform(EPSG1, EPSG2, QgsProject.instance())

        # FIELDS INDICES
        idx = self.from_layer.dataProvider().fieldNameIndex(ffield)
        fid = self.to_layer.dataProvider().fieldNameIndex(tfield)

        # We create an spatial self.index to hold all the features of the layer that will receive the data
        # And a dictionary that will hold all the features IDs found to intersect with each feature in the spatial index
        self.ProgressMaxValue.emit(self.to_layer.dataProvider().featureCount())
        self.ProgressText.emit("Building Spatial Index")
        self.ProgressValue.emit(0)
        allfeatures = {}
        merged = {}
        self.index = QgsSpatialIndex()
        for i, feature in enumerate(self.to_layer.getFeatures()):
            allfeatures[feature.id()] = feature
            merged[feature.id()] = feature
            self.index.insertFeature(feature)
            self.ProgressValue.emit(i)

        self.ProgressText.emit("Duplicating Layers")
        self.all_attr = {}
        # We create the memory layer that will have the analysis result, which is the lowest common
        # denominator of both layers
        epsg_code = int(self.to_layer.crs().authid().split(":")[1])
        if self.from_layer.wkbType() in self.poly_types and self.to_layer.wkbType() in self.poly_types:
            lcd_layer = QgsVectorLayer("MultiPolygon?crs=epsg:" + str(epsg_code), "output", "memory")
            self.output_type = "Poly"

        elif (
            self.from_layer.wkbType() in self.poly_types + self.line_types
            and self.to_layer.wkbType() in self.poly_types + self.line_types
        ):
            lcd_layer = QgsVectorLayer("MultiLineString?crs=epsg:" + str(epsg_code), "output", "memory")
            self.output_type = "Line"
        else:
            lcd_layer = QgsVectorLayer("MultiPoint?crs=epsg:" + str(epsg_code), "output", "memory")
            self.output_type = "Point"

        lcdpr = lcd_layer.dataProvider()
        lcdpr.addAttributes(
            [
                QgsField("Part_ID", QVariant.Int),
                QgsField(ffield, self.from_layer.fields().field(idx).type()),
                QgsField(tfield, self.to_layer.fields().field(fid).type()),
                QgsField("P-" + str(ffield), QVariant.Double),  # percentage of the from field
                QgsField("P-" + str(tfield), QVariant.Double),
            ]
        )  # percentage of the to field
        lcd_layer.updateFields()

        # PROGRESS BAR
        self.ProgressMaxValue.emit(self.from_layer.dataProvider().featureCount())
        self.ProgressText.emit("Running Analysis")
        self.ProgressValue.emit(0)
        part_id = 1
        features = []
        areas = {}
        for fc, feat in enumerate(self.from_layer.getFeatures()):
            geom = feat.geometry()
            if geom is not None:
                if self.transform is not None:
                    geom = geom.transform(self.transform)
                geometry, statf = self.find_geometry(geom)
                uncovered, statf = self.find_geometry(geom)
                # uncovered = copy.deepcopy(geometry)

                intersecting = self.index.intersects(geometry.boundingBox())
                # Find all intersecting parts
                for f in intersecting:
                    g = geometry.intersection(allfeatures[f].geometry())
                    if g.area() > 0:
                        feature = QgsFeature()
                        geo, stati = self.find_geometry(g)
                        feature.setGeometry(geo)
                        geo, statt = self.find_geometry(allfeatures[f].geometry())
                        perct = stati / statt
                        percf = stati / statf
                        areas[f] = statt
                        feature.setAttributes(
                            [part_id, feat.attributes()[idx], allfeatures[f].attributes()[fid], percf, perct]
                        )
                        features.append(feature)

                        # prepare the data for the non overlapping
                        if uncovered is not None:
                            uncovered = uncovered.difference(g)
                            aux = merged[f].geometry().difference(g)
                            if aux is not None:
                                merged[f].setGeometry(aux)
                            part_id += 1

                # Find the part that does not intersect anything
                if uncovered is not None:
                    if uncovered.area() > 0:
                        feature = QgsFeature()
                        geo, stati = self.find_geometry(uncovered)
                        feature.setGeometry(geo)
                        perct = 0
                        percf = stati / statf
                        feature.setAttributes([part_id, feat.attributes()[idx], "", percf, perct])
                        features.append(feature)
                        part_id += 1

            self.ProgressValue.emit(fc)
            self.ProgressText.emit(
                "Running Analysis (" + "{:,}".format(fc) + "/" + "{:,}".format(self.from_layer.featureCount()) + ")"
            )

        # Find the features on TO that have no correspondence in FROM
        for f, feature in merged.items():
            geom = feature.geometry()
            if geom.area() > 0:
                feature = QgsFeature()
                geo, stati = self.find_geometry(geom)
                feature.setGeometry(geo)
                perct = stati / areas[f]
                percf = 0
                feature.setAttributes([part_id, "", allfeatures[f].attributes()[fid], percf, perct])
                features.append(feature)
                part_id += 1

        if features:
            a = lcdpr.addFeatures(features)
        self.result = lcd_layer

        self.ProgressValue.emit(self.from_layer.dataProvider().featureCount())
        self.finished_threaded_procedure.emit("procedure")

    def find_geometry(self, g):
        if self.output_type == "Poly":
            stat = g.area()
            if g.isMultipart():
                geometry = QgsGeometry.fromMultiPolygonXY(g.asMultiPolygon())
            else:
                geometry = QgsGeometry.fromPolygonXY(g.asPolygon())
        elif self.output_type == "Line":
            stat = g.length()
            if g.isMultipart():
                geometry = QgsGeometry.fromMultiPolylineXY(g.asMultiPolyLine())
            else:
                geometry = QgsGeometry.fromPolyline(g.asPoly())
        else:
            stat = 1
            if g.isMultipart():
                geometry = QgsGeometry.fromMultiPointXY(g.asMultiPoint())
            else:
                geometry = QgsGeometry.fromPointXY(g.asPoint())
        return geometry, stat

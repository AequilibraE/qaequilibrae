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
from PyQt4.QtCore import QVariant, SIGNAL
from qgis.core import QgsCoordinateTransform, QgsSpatialIndex, QgsFeature, QgsGeometry, QgsField, QgsVectorLayer

from auxiliary_functions import *
from global_parameters import *
from worker_thread import WorkerThread


class LeastCommonDenominatorProcedure(WorkerThread):
    def __init__(self, parentThread, flayer, tlayer, ffield, tfield):
        WorkerThread.__init__(self, parentThread)
        self.flayer = flayer
        self.tlayer = tlayer
        self.ffield = ffield
        self.tfield = tfield
        self.error = None
        self.poly_types = poly_types + multi_poly
        self.line_types = line_types + multi_line
        self.point_types = point_types + multi_point
        self.result = None

    def doWork(self):
        flayer = self.flayer
        tlayer = self.tlayer
        ffield = self.ffield
        tfield = self.tfield

        self.from_layer = get_vector_layer_by_name(flayer)
        self.to_layer = get_vector_layer_by_name(tlayer)

        self.transform = None
        if self.from_layer.dataProvider().crs() != self.to_layer.dataProvider().crs():
            self.transform = QgsCoordinateTransform(self.from_layer.dataProvider().crs(),
                                                    self.to_layer.dataProvider().crs())

        # FIELDS INDICES
        idx = self.from_layer.fieldNameIndex(ffield)
        fid = self.to_layer.fieldNameIndex(tfield)

        # We create an spatial self.index to hold all the features of the layer that will receive the data
        # And a dictionary that will hold all the features IDs found to intersect with each feature in the spatial index
        allfeatures = {feature.id(): feature for (feature) in self.to_layer.getFeatures()}
        self.index = QgsSpatialIndex()
        for feature in allfeatures.values():
            self.index.insertFeature(feature)
        self.all_attr = {}

        # We create the memory layer that will have the analysis result, which is the lowest common
        # denominator of both layers
        epsg_code = int(self.to_layer.crs().authid().split(":")[1])
        if self.from_layer.wkbType() in self.poly_types and self.to_layer.wkbType() in self.poly_types:
            lcd_layer = QgsVectorLayer("MultiPolygon?crs=epsg:" + str(epsg_code), "output", "memory")
            self.output_type = 'Poly'

        elif self.from_layer.wkbType() in self.poly_types + self.line_types and \
             self.to_layer.wkbType() in self.poly_types + self.line_types:
            lcd_layer = QgsVectorLayer("MultiLineString?crs=epsg:" + str(epsg_code), "output", "memory")
            self.output_type = 'Line'
        else:
            lcd_layer = QgsVectorLayer("MultiPoint?crs=epsg:" + str(epsg_code), "output", "memory")
            self.output_type = 'Point'

        lcdpr = lcd_layer.dataProvider()
        lcdpr.addAttributes([QgsField("Part_ID", QVariant.Int),
                             QgsField(ffield, self.from_layer.fields().field(idx).type()),
                             QgsField(tfield, self.to_layer.fields().field(fid).type()),
                             QgsField('P-' + str(ffield) , QVariant.Double), # percentage of the from field
                             QgsField('P-' + str(tfield), QVariant.Double)]) # percentage of the to field
        lcd_layer.updateFields()

        # PROGRESS BAR
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.from_layer.dataProvider().featureCount())

        part_id = 1
        features = []
        for fc, feat in enumerate(self.from_layer.getFeatures()):
            geom = feat.geometry()
            if geom is not None:
                if self.transform is not None:
                    a = geom.transform(self.transform)
                geometry, statf = self.find_geometry(geom)

                intersecting = self.index.intersects(geom.boundingBox())
                for f in intersecting:
                    g = geom.intersection(allfeatures[f].geometry())
                    if g.area() > 0:
                        feature = QgsFeature()
                        geo, stati = self.find_geometry(g)
                        feature.setGeometry(geo)
                        geo, statt = self.find_geometry(allfeatures[f].geometry())
                        perct = stati / statt
                        percf = stati / statf
                        feature.setAttributes([part_id,
                                               feat.attributes()[idx],
                                               allfeatures[f].attributes()[fid],
                                               percf,
                                               perct])
                        features.append(feature)
                        part_id += 1
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), fc)
        if features:
            a = lcdpr.addFeatures(features)
        self.result = lcd_layer

        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), self.from_layer.dataProvider().featureCount())
        self.emit(SIGNAL("finished_threaded_procedure( PyQt_PyObject )"), "procedure")

    def find_geometry(self, g):
        if self.output_type == 'Poly':
            stat = g.area()
            if g.isMultipart():
                geometry = QgsGeometry.fromMultiPolygon(g.asMultiPolygon())
            else:
                geometry = QgsGeometry.fromPolygon(g.asPolygon())
        elif self.output_type == 'Line':
            stat = g.length()
            if g.isMultipart():
                geometry = QgsGeometry.fromMultiLineString(g.asMultiPoly())
            else:
                geometry = QgsGeometry.fromLineString(g.asPoly())
        else:
            stat = 1
            if g.isMultipart():
                geometry = QgsGeometry.fromMultiPoint(g.asMultiPoint())
            else:
                geometry = QgsGeometry.fromPoint(g.asPoint())
        return geometry, stat

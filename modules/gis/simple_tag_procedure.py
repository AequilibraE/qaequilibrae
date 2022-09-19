import numpy as np
from aequilibrae.utils.worker_thread import WorkerThread

from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsSpatialIndex, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
from ..common_tools import get_vector_layer_by_name
from ..common_tools.global_parameters import multi_line, multi_point, line_types, point_types


class SimpleTAG(WorkerThread):
    ProgressText = pyqtSignal(object)
    ProgressValue = pyqtSignal(object)
    ProgressMaxValue = pyqtSignal(object)
    finished_threaded_procedure = pyqtSignal(object)

    def __init__(self, parentThread, flayer, tlayer, ffield, tfield, fmatch, tmatch, operation, geo_types):
        WorkerThread.__init__(self, parentThread)
        self.ffield = ffield
        self.tfield = tfield
        self.fmatch = fmatch
        self.tmatch = tmatch
        self.operation = operation
        self.geo_types = geo_types
        self.transform = None
        self.error = None
        self.from_layer = get_vector_layer_by_name(flayer)
        self.to_layer = get_vector_layer_by_name(tlayer)

        # Layer types
        if self.from_layer.wkbType() in point_types + multi_point:
            self.ftype = "point"
        elif self.from_layer.wkbType() in line_types + multi_line:
            self.ftype = "line"
        else:
            self.ftype = "area"

        if self.to_layer.wkbType() in point_types + multi_point:
            self.ttype = "point"
        elif self.to_layer.wkbType() in line_types + multi_line:
            self.ttype = "line"
        else:
            self.ttype = "area"

        # Search parameters
        self.sequence_of_searches = [1, 5, 10, 20]  # The second element of this list is the number of nearest
        # neighbors that will have actual distances computed for
        # in order to find the actual nearest neighor (avoid the error)
        # of the spatial index

        self.index = QgsSpatialIndex()
        self.index_from = QgsSpatialIndex()
        self.from_features = {}

    def doWork(self):
        self.ProgressText.emit("Initializing. Sit tight")
        self.ProgressValue.emit(0)

        EPSG1 = QgsCoordinateReferenceSystem(int(self.from_layer.crs().authid().split(":")[1]))
        EPSG2 = QgsCoordinateReferenceSystem(int(self.to_layer.crs().authid().split(":")[1]))
        if EPSG1 != EPSG2:
            self.transform = QgsCoordinateTransform(EPSG1, EPSG2, QgsProject.instance())

        # PROGRESS BAR
        self.ProgressMaxValue.emit(self.to_layer.dataProvider().featureCount())

        # FIELDS INDICES
        idx = self.from_layer.dataProvider().fieldNameIndex(self.ffield)
        fid = self.to_layer.dataProvider().fieldNameIndex(self.tfield)
        if self.fmatch is not None:
            idq = self.from_layer.dataProvider().fieldNameIndex(self.fmatch)
            idq2 = self.to_layer.dataProvider().fieldNameIndex(self.tmatch)

            self.from_match = {feature.id(): feature.attributes()[idq] for (feature) in self.from_layer.getFeatures()}
            self.to_match = {feature.id(): feature.attributes()[idq2] for (feature) in self.to_layer.getFeatures()}

        # We create an spatial self.index to hold all the features of the layer that will receive the data
        self.ProgressText.emit("Spatial index for target layer")
        self.ProgressValue.emit(0)
        allfeatures = {}
        for i, feature in enumerate(self.to_layer.getFeatures()):
            self.index.addFeature(feature)
            allfeatures[feature.id()] = feature
            self.ProgressValue.emit(i)
        self.all_attr = {}

        # Appending the line below would secure perfect results, but yields a VERY slow algorithm for when
        # matches are not found
        # self.sequence_of_searches.append(self.from_count)

        # Dictionary with the FROM values
        self.ProgressMaxValue.emit(self.from_layer.dataProvider().featureCount())
        self.ProgressText.emit("Spatial index for source layer")
        self.from_val = {}
        for i, feature in enumerate(self.from_layer.getFeatures()):
            self.index_from.addFeature(feature)
            self.ProgressValue.emit(i)
            self.from_val[feature.id()] = feature.attributes()[idx]
            self.from_features[feature.id()] = feature

        # The spatial self.index for source layer
        self.ProgressValue.emit(0)

        self.from_count = len(self.from_val.keys())  # Number of features in the source layer
        self.ProgressText.emit("Performing spatial matching")
        self.ProgressValue.emit(0)
        self.ProgressMaxValue.emit(self.to_layer.dataProvider().featureCount())
        # Now we will have the code for all the possible configurations of input layer and output layer
        for i, feat in enumerate(self.to_layer.getFeatures()):
            self.ProgressValue.emit(i)

            self.chooses_match(feat)
            if feat.id() not in self.all_attr:
                self.all_attr[feat.id()] = None

        self.ProgressValue.emit(0)
        self.ProgressText.emit("Writing data to target layer")
        for i, feat in enumerate(self.to_layer.getFeatures()):
            self.ProgressValue.emit(i)
            if self.all_attr[feat.id()] is not None:
                _ = self.to_layer.dataProvider().changeAttributeValues({feat.id(): {fid: self.all_attr[feat.id()]}})

        self.to_layer.commitChanges()
        self.to_layer.updateFields()

        self.ProgressValue.emit(self.to_layer.dataProvider().featureCount())
        self.finished_threaded_procedure.emit("procedure")

    def chooses_match(self, feat):
        geom = feat.geometry()
        if geom is None:
            return

        if self.transform is not None:
            geom.transform(self.transform)

        if self.operation in ["ENCLOSED", "TOUCHING"]:
            self.enclosed_or_touching(feat, geom)
        else:
            self.other_predicates(feat, geom)

    def other_predicates(self, feat, geom):
        # The problem with the "nearest" search is that we cannot swear by it when we are using only spatial
        # indexes. For this reason we will compute a fixed number of nearest neighbors and then get the
        # distance for each one of them
        pt = geom.centroid().asPoint()
        s = self.sequence_of_searches[1]
        nearest = self.index_from.nearestNeighbor(pt, s)
        dists = np.zeros(len(nearest))
        for k, n in enumerate(nearest):
            dists[k] = self.from_features[n].geometry().distance(geom)
        min_index = np.argsort(dists)
        if feat.id() not in self.all_attr:
            for k in range(len(nearest)):
                n = nearest[min_index[k]]
                if self.fmatch:
                    if self.from_match[feat.id()] == self.to_match[n]:
                        self.all_attr[feat.id()] = self.from_val[n]
                        break
                else:
                    self.all_attr[feat.id()] = self.from_val[n]
                    break

    def enclosed_or_touching(self, feat, geom):
        nearest = self.index_from.intersects(geom.boundingBox())
        if self.fmatch:
            nearest = [n for n in nearest if self.from_match[feat.id()] == self.to_match[n]]
        if self.operation == "ENCLOSED":
            if self.geo_types[0] == "polygon":
                for n in nearest:
                    if self.from_features[n].geometry().contains(geom):
                        self.all_attr[feat.id()] = self.from_val[n]
                        break
            # if we destination was the polygon
            else:
                for n in nearest:
                    if geom.contains(self.from_features[n].geometry()):
                        self.all_attr[feat.id()] = self.from_val[n]
                        break
        else:
            # we will compute the overlaps to make sure we are keeping the best match. e.g. Largest area or largest
            # length
            current_max = [None, -1]
            intersec = "length"
            if self.geo_types == ["polygon", "polygon"]:
                intersec = "area"

            for n in nearest:
                intersection = self.from_features[n].geometry().intersection(geom)
                if intersection.geometry() is not None:
                    if intersec == "length":
                        aux = intersection.geometry().length()
                    else:
                        aux = intersection.geometry().area()
                    if aux > current_max[1]:
                        current_max = [self.from_val[n], aux]
            if current_max[0] is not None:
                self.all_attr[feat.id()] = current_max[0]

"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Compute GIS tags
 Purpose:    Implements computation of GIS tags on a separate thread

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4.QtCore import *
import numpy as np
from auxiliary_functions import *
from global_parameters import *
from worker_thread import WorkerThread


def main():
    pass


class SimpleTAG(WorkerThread):
    def __init__(self, parentThread, flayer, tlayer, ffield, tfield, fmatch, tmatch, operation):
        WorkerThread.__init__(self, parentThread)
        self.flayer = flayer
        self.tlayer = tlayer
        self.ffield = ffield
        self.tfield = tfield
        self.fmatch = fmatch
        self.tmatch = tmatch
        self.operation = operation
        self.error = None

        self.sequence_of_searches = [1, 5, 10, 20]  # The second element of this list is the number of nearest
                                                    # neighbors that will have actual distances computed for
                                                    # in order to find the actual nearest neighor (avoid the error)
                                                    # of the spatial index
    def doWork(self):
        flayer = self.flayer
        tlayer = self.tlayer
        ffield = self.ffield
        tfield = self.tfield
        tmatch = self.tmatch

        self.from_layer = get_vector_layer_by_name(flayer)
        self.to_layer = get_vector_layer_by_name(tlayer)

        self.transform = None
        if self.from_layer.dataProvider().crs() != self.to_layer.dataProvider().crs():
            self.transform = QgsCoordinateTransform(self.from_layer.dataProvider().crs(),
                                                    self.to_layer.dataProvider().crs())

        # PROGRESS BAR
        self.emit( SIGNAL( "ProgressMaxValue( PyQt_PyObject )" ), self.to_layer.dataProvider().featureCount())

        # FIELDS INDICES
        idx = self.from_layer.fieldNameIndex(ffield)
        fid = self.to_layer.fieldNameIndex(tfield)
        if self.fmatch is not None:
            idq = self.from_layer.fieldNameIndex(self.fmatch)
            idq2 = self.to_layer.fieldNameIndex(tmatch)
            
            self.from_match = {feature.id(): feature.attributes()[idq] for (feature) in self.from_layer.getFeatures()}
            self.to_match = {feature.id(): feature.attributes()[idq2] for (feature) in self.to_layer.getFeatures()}

        # We create an spatial self.index to hold all the features of the layer that will receive the data
        # And a dictionary that will hold all the features IDs found to intersect with each feature in the spatial index
        allfeatures = {feature.id(): feature for (feature) in self.to_layer.getFeatures()}
        self.index = QgsSpatialIndex()
        for feature in allfeatures.values():
            self.index.insertFeature(feature)
        self.all_attr = {}
        
        # Dictionary with the FROM values
        self.from_val = {feature.id(): feature.attributes()[idx] for (feature) in self.from_layer.getFeatures()}
        self.from_count = len(self.from_val.keys()) #Number of features in the source layer

        # Appending the line below would secure perfect results, but yields a VERY slow algorithm for when
        # matches are not found
        # self.sequence_of_searches.append(self.from_count)

        # The spatial self.index for source layer
        self.from_features = {feature.id(): feature for (feature) in self.from_layer.getFeatures()}
        self.index_from = QgsSpatialIndex()

        for feat in self.from_features.values():
            self.index_from.insertFeature(feat)

        #Now we will have the code for all the possible configurations of input layer and output layer

    #If target layer is a point layer
        for i, feat in enumerate(self.to_layer.getFeatures()):
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), i)

            self.chooses_match(feat)
            if feat.id() not in self.all_attr:
                self.all_attr[feat.id()] = None

        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), 0)
        for i, feat in enumerate(self.to_layer.getFeatures()):
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), i)
            if self.all_attr[feat.id()] is not None:
                a = self.to_layer.dataProvider().changeAttributeValues({feat.id(): {fid: self.all_attr[feat.id()]}})

        self.to_layer.commitChanges()
        self.to_layer.updateFields()
        
        self.emit( SIGNAL( "ProgressValue( PyQt_PyObject )" ), self.to_layer.dataProvider().featureCount())
        self.emit( SIGNAL( "finished_threaded_procedure( PyQt_PyObject )" ), "procedure")

    def chooses_match(self, feat):
        geom = feat.geometry()
        if self.transform is not None:
            geom.transform(self.transform)

        if self.operation in ["ENCLOSED", "TOUCHING"]:
            nearest = self.index_from.intersects(geom.boundingBox())

            if self.fmatch:
                near2 = []
                for n in nearest:
                    if self.from_match[feat.id()] == self.to_match[n]:
                        near2.append(n)
                nearest = near2

            if self.operation == "ENCLOSED":
                for n in nearest:
                    if self.from_features[n].geometry().contains(geom):
                        self.all_attr[feat.id()] = self.from_val[n]
                        break
            else:
                # we will compute the overlaps to make sure we are keeping the best match. e.g. Largest area or largest
                # length
                current_max = [None, -1]
                relevant_types = line_types + poly_types
                ranking = False
                if self.from_layer.wkbType() in relevant_types and self.to_layer.wkbType() in relevant_types:
                    ranking = True
                    intersec = 'length'
                    if self.from_layer.wkbType() in poly_types and self.to_layer.wkbType() in poly_types:
                        intersec = 'area'

                for n in nearest:
                    if ranking:
                        intersection = self.from_features[n].geometry().intersection(geom)
                        if intersection.geometry() is not None:
                            if intersec == 'length':
                                aux = intersection.geometry().length()
                            else:
                                aux = intersection.geometry().area()
                            if aux > current_max[1]:
                                current_max[0] = self.from_val[n]
                                current_max[1] = aux
                if current_max[0] is not None:
                    self.all_attr[feat.id()] = current_max[0]
        else:
            # The problem with the "nearest" search is that we cannot swear by it when we are using only spatial
            # indexes. For this reason we will compute a fixed number of nearest neighbors and then get the
            # distance for each one of them
            pt = geom.centroid()
            s = self.sequence_of_searches[1]
            nearest = self.index_from.nearestNeighbor(pt, s)
            dists = np.zeros(len(nearest))

            for k, n in enumerate(nearest):
                dists[k] = self.from_features[n].geometry().distance(geom)
            min_index = np.argsort(dists)

            for k in range(len(nearest)):
                n = nearest[min_index[k]]
                if self.fmatch:
                    if self.from_match[feat.id()] == self.to_match[n]:
                        self.all_attr[feat.id()] = self.from_val[n]
                        break
                else:
                    self.all_attr[feat.id()] = self.from_val[n]
                    break
                if feat.id() in self.all_attr:
                    break


if __name__ == '__main__':
    main()

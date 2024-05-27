__author__ = "Arthur Evrard"

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

provider_path = os.path.dirname(__file__)[:-28]


class Provider(QgsProcessingProvider):
    def __init__(self, translator):
        super(QgsProcessingProvider, self).__init__()
        self.tr = translator

    def loadAlgorithms(self):
        from .matrix_from_layer import MatrixFromLayer
        from .export_matrix import exportMatrix
        from .project_from_layers import ProjectFromLayer
        from .renumber_from_centroids import RenumberFromCentroids
        from .Add_connectors import AddConnectors
        from .assign_from_yaml import TrafficAssignYAML

        self.addAlgorithm(MatrixFromLayer(self.tr))
        self.addAlgorithm(exportMatrix(self.tr))
        self.addAlgorithm(ProjectFromLayer(self.tr))
        self.addAlgorithm(RenumberFromCentroids(self.tr))
        self.addAlgorithm(AddConnectors(self.tr))
        self.addAlgorithm(TrafficAssignYAML(self.tr))
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        """The ID used for identifying the provider.
        This string should be a unique, short, character only string,
        eg "qgis" or "gdal". This string should not be localised.
        """
        return "AequilibraE"

    def name(self):
        """The human friendly name of the plugin in Processing.
        This string should be as short as possible (e.g. "Lastools", not
        "Lastools version 1.0.1 64-bit") and localised.
        """
        return "AequilibraE"

    def icon(self):
        """Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QIcon(os.path.join(provider_path, "icon.png"))

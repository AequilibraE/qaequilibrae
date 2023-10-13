__author__ = 'Arthur Evrard'

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

ProviderPath = os.path.dirname(__file__)

from .omx2csv import omx2csv
from .ProjectFromLayer import ProjectFromLayer
from .RenumberFromCentroids import RenumberFromCentroids

class Provider(QgsProcessingProvider):

    def loadAlgorithms(self):
        self.addAlgorithm(omx2csv())
        self.addAlgorithm(ProjectFromLayer())
        self.addAlgorithm(RenumberFromCentroids())
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        """The ID used for identifying the provider.
        This string should be a unique, short, character only string,
        eg "qgis" or "gdal". This string should not be localised.
        """
        return 'qAequilibraE'

    def name(self):
        """The human friendly name of the plugin in Processing.
        This string should be as short as possible (e.g. "Lastools", not
        "Lastools version 1.0.1 64-bit") and localised.
        """
        return self.tr('qAequilibraE')

    def icon(self):
        """Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QIcon(os.path.join(ProviderPath, "icon.png"))
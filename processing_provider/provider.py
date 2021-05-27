__author__ = 'Arthur Evrard'

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

ProviderPath = os.path.dirname(__file__)

from .Create_Nodes import CreateNodes
from .Create_SingleConnectors import CreateSingleConnectors
from .NodesID2Links import AddNodeInformationsToLinks

class Provider(QgsProcessingProvider):

    def loadAlgorithms(self):
        self.addAlgorithm( CreateNodes() )
        self.addAlgorithm( CreateSingleConnectors() )
        self.addAlgorithm( AddNodeInformationsToLinks() )
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        """The ID used for identifying the provider.
        This string should be a unique, short, character only string,
        eg "qgis" or "gdal". This string should not be localised.
        """
        return 'AequilibraE'

    def name(self):
        """The human friendly name of the plugin in Processing.
        This string should be as short as possible (e.g. "Lastools", not
        "Lastools version 1.0.1 64-bit") and localised.
        """
        return self.tr('AequilibraE')

    def icon(self):
        """Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QIcon(os.path.join(ProviderPath, "icon.png"))
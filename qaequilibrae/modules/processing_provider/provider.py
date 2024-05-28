__author__ = "Arthur Evrard"

from os.path import join
import sys
from pathlib import Path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

provider_path = Path(__file__).parent.parent.parent
if str(provider_path) not in sys.path:
    sys.path.append(str(provider_path))


class Provider(QgsProcessingProvider):

    def loadAlgorithms(self):
        from .Add_connectors import AddConnectors
        from .assign_from_yaml import TrafficAssignYAML
        from .export_matrix import ExportMatrix
        from .matrix_from_layer import MatrixFromLayer
        from .project_from_layer import ProjectFromLayer
        from .renumber_from_centroids import RenumberNodesFromCentroids

        self.addAlgorithm(MatrixFromLayer())
        self.addAlgorithm(ExportMatrix())
        self.addAlgorithm(ProjectFromLayer())
        self.addAlgorithm(RenumberNodesFromCentroids())
        self.addAlgorithm(AddConnectors())
        self.addAlgorithm(TrafficAssignYAML())

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
        return QIcon(join(provider_path, "icon.png"))

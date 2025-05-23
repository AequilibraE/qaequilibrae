__author__ = "Arthur Evrard"

import sys
from os.path import join
from pathlib import Path

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider

provider_path = Path(__file__).parent.parent.parent
if str(provider_path) not in sys.path:
    sys.path.append(str(provider_path))


class Provider(QgsProcessingProvider):

    def loadAlgorithms(self):
        from .Add_connectors import AddConnectors
        from .add_links_from_layer import AddLinksFromLayer
        from .add_matrix_from_layer import AddMatrixFromLayer
        from .assign_transit_from_yaml import TransitAssignYAML
        from .assign_traffic_from_yaml import TrafficAssignYAML
        from .create_matrix_from_layer import CreateMatrixFromLayer
        from .create_transit_graph import CreatePTGraph
        from .export_matrix import ExportMatrix
        from .import_gtfs import ImportGTFS
        from .matrix_calculator import MatrixCalculator
        from .project_from_layer import ProjectFromLayer
        from .project_from_OSM import ProjectFromOSM
        from .renumber_nodes_from_layer import RenumberNodesFromLayer
        from .trip_length_distribution import TripLengthDistribution

        self.addAlgorithm(AddConnectors())
        self.addAlgorithm(AddLinksFromLayer())
        self.addAlgorithm(AddMatrixFromLayer())
        self.addAlgorithm(TransitAssignYAML())
        self.addAlgorithm(TrafficAssignYAML())
        self.addAlgorithm(CreateMatrixFromLayer())
        self.addAlgorithm(CreatePTGraph())
        self.addAlgorithm(ExportMatrix())
        self.addAlgorithm(ImportGTFS())
        self.addAlgorithm(MatrixCalculator())
        self.addAlgorithm(ProjectFromLayer())
        self.addAlgorithm(ProjectFromOSM())
        self.addAlgorithm(RenumberNodesFromLayer())
        self.addAlgorithm(TripLengthDistribution())

    def id(self):
        """The ID used for identifying the provider.
        This string should be a unique, short, character only string,
        eg "qgis" or "gdal". This string should not be localised.
        """
        return "aequilibrae"

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

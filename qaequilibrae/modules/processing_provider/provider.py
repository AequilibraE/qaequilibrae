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

        self.__load_matrix_procedures()
        self.__load_network()
        self.__load_paths_procedures()
        self.__load_project_procedures()
        self.__load_public_transport_procedures()

    def __load_matrix_procedures(self):

        from .add_matrix_from_layer import AddMatrixFromLayer
        from .create_matrix_from_layer import CreateMatrixFromLayer
        from .export_matrix import ExportMatrix
        from .matrix_calculator import MatrixCalculator

        self.addAlgorithm(AddMatrixFromLayer())
        self.addAlgorithm(CreateMatrixFromLayer())
        self.addAlgorithm(ExportMatrix())
        self.addAlgorithm(MatrixCalculator())

    def __load_network(self):

        from .Add_connectors import AddConnectors
        from .add_links_from_layer import AddLinksFromLayer
        from .network_simplifier import NetworkSimplifier
        from .collapse_links import CollapseLinks
        from .renumber_nodes_from_layer import RenumberNodesFromLayer
        from .trip_length_distribution import TripLengthDistribution

        self.addAlgorithm(AddConnectors())
        self.addAlgorithm(AddLinksFromLayer())
        self.addAlgorithm(CollapseLinks())
        self.addAlgorithm(NetworkSimplifier())
        self.addAlgorithm(RenumberNodesFromLayer())
        self.addAlgorithm(TripLengthDistribution())

    def __load_paths_procedures(self):

        from .assign_traffic_from_yaml import TrafficAssignYAML

        self.addAlgorithm(TrafficAssignYAML())

    def __load_project_procedures(self):

        from .project_from_layer import ProjectFromLayer
        from .project_from_OSM import ProjectFromOSM
        from .run_module import RunProcedures

        self.addAlgorithm(ProjectFromLayer())
        self.addAlgorithm(ProjectFromOSM())
        self.addAlgorithm(RunProcedures())

    def __load_public_transport_procedures(self):

        from .assign_transit_from_yaml import TransitAssignYAML
        from .create_transit_graph import CreatePTGraph
        from .import_gtfs import ImportGTFS

        self.addAlgorithm(TransitAssignYAML())
        self.addAlgorithm(CreatePTGraph())
        self.addAlgorithm(ImportGTFS())

    def id(self):
        """The ID used for identifying the provider."""
        return "qaequilibrae"

    def name(self):
        """The human friendly name of the plugin in Processing."""
        return "QAequilibraE"

    def icon(self):
        """SQIcon used for the provider inside the Processing toolbox."""
        return QIcon(join(provider_path, "icon.png"))

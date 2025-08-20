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
        self.__load_model_building()
        self.__load_public_transport_procedures()

    def __load_matrix_procedures(self):

        from .matrix_procedures.add_matrix_from_layer import MatrixFromLayer
        from .matrix_procedures.export_matrix import ExportMatrix
        from .matrix_procedures.matrix_calculator import MatrixCalculator

        self.addAlgorithm(MatrixFromLayer())
        self.addAlgorithm(ExportMatrix())
        self.addAlgorithm(MatrixCalculator())

    def __load_network(self):

        from .network.add_links_from_layer import AddLinksFromLayer
        from .network.collapse_links import CollapseLinks
        from .network.network_simplifier import NetworkSimplifier
        from .network.renumber_nodes_from_layer import RenumberNodesFromLayer
        from .network.trip_length_distribution import TripLengthDistribution

        self.addAlgorithm(AddLinksFromLayer())
        self.addAlgorithm(CollapseLinks())
        self.addAlgorithm(NetworkSimplifier())
        self.addAlgorithm(RenumberNodesFromLayer())
        self.addAlgorithm(TripLengthDistribution())

    def __load_paths_procedures(self):

        from .paths_procedures.assign_traffic_from_yaml import TrafficAssignYAML

        self.addAlgorithm(TrafficAssignYAML())

    def __load_project_procedures(self):

        from .project_procedures.open_project import OpenProject
        from .project_procedures.create_examples import CreateExamples
        from .project_procedures.load_parameters import LoadProjectParameters
        from .project_procedures.load_log import LoadProjectLogFile
        from .project_procedures.run_module import RunProcedures
        from .project_procedures.close_project import CloseProject

        self.addAlgorithm(OpenProject())
        self.addAlgorithm(CreateExamples())
        self.addAlgorithm(LoadProjectParameters())
        self.addAlgorithm(LoadProjectLogFile())
        self.addAlgorithm(RunProcedures())
        self.addAlgorithm(CloseProject())

    def __load_model_building(self):

        from .model_building.project_from_layer import ProjectFromLayer
        from .model_building.project_from_OSM import ProjectFromOSM
        from .model_building.Add_connectors import AddConnectors

        self.addAlgorithm(ProjectFromLayer())
        self.addAlgorithm(ProjectFromOSM())
        self.addAlgorithm(AddConnectors())

    def __load_public_transport_procedures(self):

        from .public_transport_procedures.assign_transit_from_yaml import TransitAssignYAML
        from .public_transport_procedures.import_gtfs import ImportGTFS

        self.addAlgorithm(TransitAssignYAML())
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

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

        self.__load_project_procedures()
        self.__load_model_building()
        self.__load_matrix_procedures()
        self.__load_routing_procedures()
        self.__load_traffic_assignment_procedures()
        self.__load_route_choice()
        self.__load_transit_procedures()
        self.__load_gis()
        self.__load_paths_procedures()
        self.__load_distribution_procedures()

    def __load_project_procedures(self):

        from .project_procedures.close_project import CloseProject
        from .project_procedures.create_examples import CreateExamples
        from .project_procedures.create_scenarios import CreateScenarios
        from .project_procedures.load_log import LoadProjectLogFile
        from .project_procedures.load_parameters import LoadProjectParameters
        from .project_procedures.open_project import OpenProject
        from .project_procedures.run_module import RunProcedures

        self.addAlgorithm(OpenProject())
        self.addAlgorithm(CreateExamples())
        self.addAlgorithm(CreateScenarios())
        self.addAlgorithm(LoadProjectParameters())
        self.addAlgorithm(LoadProjectLogFile())
        self.addAlgorithm(RunProcedures())
        self.addAlgorithm(CloseProject())

    def __load_model_building(self):

        from .model_building.Add_connectors import AddConnectors
        from .model_building.add_links_from_layer import AddLinksFromLayer
        from .model_building.add_zones import AddZones
        from .model_building.collapse_links import CollapseLinks
        from .model_building.network_simplifier import NetworkSimplifier
        from .model_building.network_preparation import PrepareNetwork
        from .model_building.project_from_layer import ProjectFromLayer
        from .model_building.project_from_OSM import ProjectFromOSM

        self.addAlgorithm(AddConnectors())
        self.addAlgorithm(AddLinksFromLayer())
        self.addAlgorithm(AddZones())
        self.addAlgorithm(CollapseLinks())
        self.addAlgorithm(NetworkSimplifier())
        self.addAlgorithm(PrepareNetwork())
        self.addAlgorithm(ProjectFromLayer())
        self.addAlgorithm(ProjectFromOSM())

    def __load_matrix_procedures(self):

        from .matrix_procedures.export_matrix import ExportMatrix
        from .matrix_procedures.import_matrices import ImportMatrix
        from .matrix_procedures.matrix_calculator import MatrixCalculator
        from .matrix_procedures.trip_length_distribution import TripLengthDistribution

        self.addAlgorithm(ExportMatrix())
        self.addAlgorithm(ImportMatrix())
        self.addAlgorithm(MatrixCalculator())
        self.addAlgorithm(TripLengthDistribution())

    def __load_routing_procedures(self):

        from .routing_procedures.tsp import RunTSP

        self.addAlgorithm(RunTSP())

    def __load_traffic_assignment_procedures(self):

        from .assignment_procedures.traffic_assignment import TrafficAssignment

        self.addAlgorithm(TrafficAssignment())

    def __load_transit_procedures(self):

        from .transit_procedures.explore_transit import ExploreTransit
        from .transit_procedures.import_gtfs import ImportGTFS
        from .transit_procedures.transit_assignment import TransitAssignment

        self.addAlgorithm(ExploreTransit())
        self.addAlgorithm(ImportGTFS())
        self.addAlgorithm(TransitAssignment())

    def __load_gis(self):

        from .gis.desire_lines import DesireLines
        from .gis.scenario_comparison import ScenarioComparison
        from .gis.simple_tag import SimpleTag
        from .gis.stacked_bandwidth import StackedBandwidth
        from .gis.visualize_data import VisualizeData

        self.addAlgorithm(DesireLines())
        self.addAlgorithm(ScenarioComparison())
        self.addAlgorithm(SimpleTag())
        self.addAlgorithm(StackedBandwidth())
        self.addAlgorithm(VisualizeData())

    def __load_route_choice(self):

        from .route_choice.route_choice import RouteChoice

        self.addAlgorithm(RouteChoice())

    def __load_paths_procedures(self):

        from .paths_procedures.impedance_matrix import ImpedanceMatrix
        from .paths_procedures.shortest_path import ShortestPath
        from .paths_procedures.skim_viewer import SkimViewer

        self.addAlgorithm(ImpedanceMatrix())
        self.addAlgorithm(ShortestPath())
        self.addAlgorithm(SkimViewer())

    def __load_distribution_procedures(self):

        from .distribution_procedures.trip_distribution import TripDistribution

        self.addAlgorithm(TripDistribution())

    def id(self):
        """The ID used for identifying the provider."""
        return "qaequilibrae"

    def name(self):
        """The human friendly name of the plugin in Processing."""
        return "AequilibraE"

    def icon(self):
        """Icon used for the provider inside the Processing toolbox."""
        return QIcon(join(provider_path, "icon.png"))

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
        self.__load_model_building()
        self.__load_matrix_procedures()
        self.__load_paths_procedures()
        self.__load_geometry_io()
        self.__load_data_procedures()

    def __load_model_building(self):

        from .model_building.add_links_from_layer import AddLinksFromLayer
        from .model_building.collapse_links import CollapseLinks
        from .model_building.create_empty_project import CreateEmptyProject
        from .model_building.network_simplifier import NetworkSimplifier

        self.addAlgorithm(AddLinksFromLayer())
        self.addAlgorithm(CollapseLinks())
        self.addAlgorithm(CreateEmptyProject())
        self.addAlgorithm(NetworkSimplifier())

    def __load_matrix_procedures(self):

        from .matrix_procedures.export_matrix import ExportMatrix
        from .matrix_procedures.matrix_calculator import MatrixCalculator
        from .matrix_procedures.trip_length_distribution import TripLengthDistribution

        self.addAlgorithm(ExportMatrix())
        self.addAlgorithm(MatrixCalculator())
        self.addAlgorithm(TripLengthDistribution())

    def __load_paths_procedures(self):
        from .paths_procedures.shortest_path import ShortestPath
        from .paths_procedures.traffic_assignment import RunTrafficAssignment

        self.addAlgorithm(ShortestPath())
        self.addAlgorithm(RunTrafficAssignment())

    def __load_geometry_io(self):
        from .geometry_io.add import AddLinks, AddNodes, AddZones
        from .geometry_io.extract import ExtractLinks, ExtractNodes, ExtractZones
        from .geometry_io.modify import ModifyLinks, ModifyNodes, ModifyZones

        for algorithm in (
            ExtractLinks(),
            ExtractNodes(),
            ExtractZones(),
            AddLinks(),
            AddNodes(),
            AddZones(),
            ModifyLinks(),
            ModifyNodes(),
            ModifyZones(),
        ):
            self.addAlgorithm(algorithm)

    def __load_data_procedures(self):
        from .data_procedures.add_link_type import AddLinkType
        from .data_procedures.add_mode import AddMode

        self.addAlgorithm(AddLinkType())
        self.addAlgorithm(AddMode())

    def id(self):
        """The ID used for identifying the provider."""
        return "qaequilibrae"

    def name(self):
        """The human friendly name of the plugin in Processing."""
        return "AequilibraE"

    def icon(self):
        """Icon used for the provider inside the Processing toolbox."""
        return QIcon(join(provider_path, "icon.png"))

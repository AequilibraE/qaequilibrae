"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       QGIS menu
 Purpose:    Creates the QGIS menu for AequilibraE and connects with the appropriate classes

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
 Updated:    2018-08-08
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

# Import the PyQt and QGIS libraries
# noinspection PyUnresolvedReferences
import os
import sys
import qgis
import aequilibrae
# import tempfile, glob
# from qgis.core import *
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QAction

# This is how QtCore and QtGui imports change
# from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *

# from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *

from .common_tools import ParameterDialog

# from .common_tools import logger
# from .common_tools import ReportDialog
from .common_tools import AboutDialog

# from .binary_downloader_class import BinaryDownloaderDialog
from .distribution_procedures import DistributionModelsDialog

from .gis import CompareScenariosDialog
from .gis import DesireLinesDialog
from .gis import CreateBandwidthsDialog
from .gis import LeastCommonDenominatorDialog
from .gis import SimpleTagDialog

from .network import NetworkPreparationDialog
from .network import AddConnectorsDialog
# from .network import CreatesTranspoNetDialog

from .paths_procedures import GraphCreationDialog
from .paths_procedures import TrafficAssignmentDialog
from .paths_procedures import ShortestPathDialog
from .paths_procedures import ImpedanceMatrixDialog

from .matrix_procedures import LoadMatrixDialog
from .matrix_procedures import LoadDatasetDialog
from .matrix_procedures import DisplayAequilibraEFormatsDialog

# from .matrix_procedures import MatrixManipulationDialog

# from .public_transport_procedures import GtfsImportDialog


# from .aequilibrae.aequilibrae.__version__ import binary_version as VERSION

no_binary = False
old_binary = False
# try:
#     from aequilibrae.aequilibrae.paths import VERSION_COMPILED as VERSION_GRAPH
#     if VERSION != VERSION_GRAPH:
#         old_binary = True
# except:
#     no_binary = True

sys.dont_write_bytecode = True
import os.path


class AequilibraEMenu(object):
    def __init__(self, iface):
        self.iface = iface
        self.AequilibraE_menu = None
        self.network_menu = None
        self.trip_distribution_menu = None
        self.assignment_menu = None
        self.gis_tools_menu = None

    def aequilibrae_add_submenu(self, submenu):
        if self.AequilibraE_menu is not None:
            self.AequilibraE_menu.addMenu(submenu)
        else:
            self.iface.addPluginToMenu("&AequilibraE", submenu.menuAction())

    def initGui(self):
        # Removes temporary files
        self.removes_temporary_files()

        # CREATING MASTER MENU HEAD
        self.AequilibraE_menu = QtWidgets.QMenu(QCoreApplication.translate("AequilibraE", "AequilibraE"))
        self.iface.mainWindow().menuBar().insertMenu(self.iface.firstRightStandardMenu().menuAction(),
                                                     self.AequilibraE_menu)

        # # ########################################################################
        # # ################# NETWORK MANIPULATION SUB-MENU  #######################

        self.network_menu = QtWidgets.QMenu(QCoreApplication.translate("AequilibraE", "&Network Manipulation"))
        self.aequilibrae_add_submenu(self.network_menu)

        # Network preparation
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_network.png")
        self.network_prep_action = QAction(icon, u"Network Preparation", self.iface.mainWindow())
        self.network_prep_action.triggered.connect(self.run_net_prep)
        self.network_prep_action.setEnabled(True)
        self.network_menu.addAction(self.network_prep_action)

        # Adding Connectors
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_network.png")
        self.add_connectors_action = QAction(icon, u"Adding Connectors", self.iface.mainWindow())
        self.add_connectors_action.triggered.connect(self.run_add_connectors)
        self.add_connectors_action.setEnabled(True)
        self.network_menu.addAction(self.add_connectors_action)

        # # Creating TranspoNet
        # icon = QIcon(os.path.dirname(__file__) + "/icons/icon_network.png")
        # self.create_transponet_action = QAction(icon, u"Create TranspoNet", self.iface.mainWindow())
        # self.create_transponet_action.triggered.connect(self.run_create_transponet)
        # self.create_transponet_action.setEnabled(True)
        # self.network_menu.addAction(self.create_transponet_action)

        # # ########################################################################
        # # ####################  DATA UTILITIES SUB-MENU  #########################

        self.matrix_menu = QtWidgets.QMenu(QCoreApplication.translate("AequilibraE", "&Data"))
        self.aequilibrae_add_submenu(self.matrix_menu)

        # Displaying Aequilibrae custom data formats
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_display_custom_formats.png")
        self.display_custom_formats_action = QAction(icon, u"Display AequilibraE formats", self.iface.mainWindow())
        self.display_custom_formats_action.triggered.connect(self.run_display_aequilibrae_formats)
        self.display_custom_formats_action.setEnabled(True)
        self.matrix_menu.addAction(self.display_custom_formats_action)

        # Loading matrices
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_matrices.png")
        self.load_matrix_action = QAction(icon, u"Import matrices", self.iface.mainWindow())
        self.load_matrix_action.triggered.connect(self.run_load_matrices)
        self.load_matrix_action.setEnabled(True)
        self.matrix_menu.addAction(self.load_matrix_action)

        # # Loading Database
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_dataset.png")
        self.load_database_action = QAction(icon, u"Import dataset", self.iface.mainWindow())
        self.load_database_action.triggered.connect(self.run_load_database)
        self.load_database_action.setEnabled(True)
        self.matrix_menu.addAction(self.load_database_action)

        # # # ########################################################################
        # # # ##################  TRIP DISTRIBUTION SUB-MENU  ########################

        self.trip_distribution_menu = QtWidgets.QMenu(QCoreApplication.translate("AequilibraE", "&Trip Distribution"))
        self.aequilibrae_add_submenu(self.trip_distribution_menu)

        # # IPF
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_ipf.png")
        self.ipf_action = QAction(icon, u"Iterative proportional fitting", self.iface.mainWindow())
        self.ipf_action.triggered.connect(self.run_ipf)
        self.ipf_action.setEnabled(True)
        self.trip_distribution_menu.addAction(self.ipf_action)

        # # Apply Gravity
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_apply_gravity.png")
        self.apply_gravity_action = QAction(icon, u"Apply Gravity Model", self.iface.mainWindow())
        self.apply_gravity_action.triggered.connect(self.run_apply_gravity)
        self.apply_gravity_action.setEnabled(True)
        self.trip_distribution_menu.addAction(self.apply_gravity_action)

        # # Calibrate Gravity
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_calibrate_gravity.png")
        self.calibrate_gravity_action = QAction(icon, u"Calibrate Gravity Model", self.iface.mainWindow())
        self.calibrate_gravity_action.triggered.connect(self.run_calibrate_gravity)
        self.calibrate_gravity_action.setEnabled(True)
        self.trip_distribution_menu.addAction(self.calibrate_gravity_action)

        # Trip Distribution
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_distribution.png")
        self.trip_distr_action = QAction(icon, u"Trip Distribution", self.iface.mainWindow())
        self.trip_distr_action.triggered.connect(self.run_distribution_models)
        self.trip_distr_action.setEnabled(True)
        self.trip_distribution_menu.addAction(self.trip_distr_action)

        # # ########################################################################
        # # ###################  PATH COMPUTATION SUB-MENU   #######################

        self.assignment_menu = QtWidgets.QMenu(QCoreApplication.translate("AequilibraE", "&Paths and assignment"))
        self.aequilibrae_add_submenu(self.assignment_menu)

        # Graph generation
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_graph_creation.png")
        self.graph_creation_action = QAction(icon, u"Create graph", self.iface.mainWindow())
        self.graph_creation_action.triggered.connect(self.run_create_graph)
        self.graph_creation_action.setEnabled(True)
        self.assignment_menu.addAction(self.graph_creation_action)

        # Shortest path computation
        icon = QIcon(os.path.dirname(__file__) + "/icons/single_shortest_path.png")
        self.shortest_path_action = QAction(icon, u"Shortest path", self.iface.mainWindow())
        self.shortest_path_action.triggered.connect(self.run_shortest_path)
        self.shortest_path_action.setEnabled(True)
        self.assignment_menu.addAction(self.shortest_path_action)

        # Distance matrix generation
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_dist_matrix.png")
        self.dist_matrix_action = QAction(icon, u"Impedance matrix", self.iface.mainWindow())
        self.dist_matrix_action.triggered.connect(self.run_dist_matrix)
        self.dist_matrix_action.setEnabled(True)
        self.assignment_menu.addAction(self.dist_matrix_action)

        # Traffic Assignment
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_assignment.png")
        self.traffic_assignment_action = QAction(icon, u"Traffic Assignment", self.iface.mainWindow())
        self.traffic_assignment_action.triggered.connect(self.run_traffic_assig)
        self.traffic_assignment_action.setEnabled(True)
        self.assignment_menu.addAction(self.traffic_assignment_action)

        # # ########################################################################
        # # #######################  TRANSIT SUB-MENU   ###########################

        # self.transit_menu = QtWidgets.QMenu(QCoreApplication.translate("AequilibraE", "&Public Transport"))
        # self.aequilibrae_add_submenu(self.transit_menu)

        # # Graph generation
        # icon = QIcon(os.path.dirname(__file__) + "/icons/icon_import_gtfs.png")
        # self.gtfs_import_action = QAction(icon, u"Convert GTFS to SpatiaLite", self.iface.mainWindow())
        # self.gtfs_import_action.triggered.connect(self.run_import_gtfs)
        # self.gtfs_import_action.setEnabled(True)
        # self.transit_menu.addAction(self.gtfs_import_action)

        # ########################################################################
        # #################        GIS TOOLS SUB-MENU    #########################

        self.gis_tools_menu = QtWidgets.QMenu(QCoreApplication.translate("AequilibraE", "&GIS tools"))
        self.aequilibrae_add_submenu(self.gis_tools_menu)
        #
        # Node to area aggregation
        # icon = QIcon(os.path.dirname(__file__) + "/icons/icon_node_to_area.png")
        # self.node_to_area_action = QAction(icon, u"Aggregation: Node to Area", self.iface.mainWindow())
        # self.node_to_area_action.triggered.connect(self.run_node_to_area)
        # self.node_to_area_action.setEnabled(True)
        # self.gis_tools_menu.addAction(self.node_to_area_action)

        # Simple TAG
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_simple_tag.png")
        self.simple_tag_action = QAction(icon, u"Simple TAG", self.iface.mainWindow())
        self.simple_tag_action.triggered.connect(self.run_simple_tag)
        self.simple_tag_action.setEnabled(True)
        self.gis_tools_menu.addAction(self.simple_tag_action)

        # Lowest common denominator
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_lcd.png")
        self.lcd_action = QAction(icon, u"Lowest common denominator", self.iface.mainWindow())
        self.lcd_action.triggered.connect(self.run_lcd)
        self.lcd_action.setEnabled(True)
        self.gis_tools_menu.addAction(self.lcd_action)

        # Desire lines
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_desire_lines.png")
        self.dlines_action = QAction(icon, u"Desire Lines", self.iface.mainWindow())
        self.dlines_action.triggered.connect(self.run_dlines)
        self.dlines_action.setEnabled(True)
        self.gis_tools_menu.addAction(self.dlines_action)

        # Bandwidths
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_bandwidths.png")
        self.bandwidth_action = QAction(icon, u"Stacked Bandwidth", self.iface.mainWindow())
        self.bandwidth_action.triggered.connect(self.run_bandwidth)
        self.bandwidth_action.setEnabled(True)
        self.gis_tools_menu.addAction(self.bandwidth_action)

        # Scenario comparison
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_scenario_comparison.png")
        self.scenario_comparison_action = QAction(icon, u"Scenario Comparison", self.iface.mainWindow())
        self.scenario_comparison_action.triggered.connect(self.run_scenario_comparison)
        self.scenario_comparison_action.setEnabled(True)
        self.gis_tools_menu.addAction(self.scenario_comparison_action)

        # ########################################################################
        # #################          LOOSE STUFF         #########################

        # Change parameters
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_parameters.png")
        self.parameters_action = QAction(icon, u"Parameters", self.iface.mainWindow())
        self.parameters_action.triggered.connect(self.run_change_parameters)
        self.parameters_action.setEnabled(True)  # Need to add this row for all actions
        # QObject.connect(self.parameters_action, SIGNAL("triggered()"), self.run_change_parameters)
        self.AequilibraE_menu.addAction(self.parameters_action)

        # About
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_parameters.png")
        self.about_action = QAction(icon, u"About", self.iface.mainWindow())
        self.about_action.triggered.connect(self.run_about)
        self.about_action.setEnabled(True)
        self.AequilibraE_menu.addAction(self.about_action)

        # Download binaries
        if no_binary:
            icon = QIcon(os.path.dirname(__file__) + "/icons/icon_binaries.png")
            self.binary_action = QAction(icon, u"Download binaries", self.iface.mainWindow())
            self.binary_action.triggered.connect(self.run_binary_download)
            self.binary_action.setEnabled(True)
            self.AequilibraE_menu.addAction(self.binary_action)
        #
        #
        # if old_binary:
        #     report = ['You have an old version of the AequilibraE binaries']
        #     report.append('To fix this issue, please do the following:')
        #     report.append('     1. Uninstall AequilibraE')
        #     report.append('     2. Re-start QGIS')
        #     report.append('     3. Re-install AequilibraE from the official repository')
        #     report.append('     4. Download the new binaries from the Menu Aequilibrae-Download Binaries')
        #     report.append('     5. Re-start QGIS')
        #     dlg2 = ReportDialog(self.iface, report)
        #     dlg2.show()
        #     dlg2.exec_()

    #########################################################################

    def unload(self):
        self.removes_temporary_files()

        # unloads the add-on
        if self.AequilibraE_menu is not None:
            self.iface.mainWindow().menuBar().removeAction(self.AequilibraE_menu.menuAction())
        else:
            self.iface.removePluginMenu("&AequilibraE", self.network_menu.menuAction())
            self.iface.removePluginMenu("&AequilibraE", self.assignment_menu.menuAction())
            self.iface.removePluginMenu("&AequilibraE", self.transit_menu.menuAction())
            self.iface.removePluginMenu("&AequilibraE", self.trip_distribution_menu.menuAction())
            self.iface.removePluginMenu("&AequilibraE", self.gis_tools_menu.menuAction())

    def removes_temporary_files(self):
        pass
        # Removes all the temporary files from previous uses
        # p = tempfile.gettempdir() + '/aequilibrae_*'
        # for f in glob.glob(p):
        #     try:
        #         os.unlink(f)
        #     except:
        #         pass

    def run_change_parameters(self):
        dlg2 = ParameterDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_about(self):
        dlg2 = AboutDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_load_matrices(self):
        dlg2 = LoadMatrixDialog(self.iface, sparse=True, multiple=True, single_use=False)
        dlg2.show()
        dlg2.exec_()

    def run_load_database(self):
        dlg2 = LoadDatasetDialog(self.iface, single_use=False)
        dlg2.show()
        dlg2.exec_()

    def run_display_aequilibrae_formats(self):
        dlg2 = DisplayAequilibraEFormatsDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_binary_download(self):
        pass

    #     dlg2 = BinaryDownloaderDialog(self.iface)
    #     dlg2.show()
    #     dlg2.exec_()

    # run method that calls the network preparation section of the code
    def run_net_prep(self):
        dlg2 = NetworkPreparationDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        # If we wanted modal, we would eliminate the dlg2.show()

    # run method that calls the network preparation section of the code
    def run_create_transponet(self):
        pass

    #     dlg2 = CreatesTranspoNetDialog(self.iface)
    #     dlg2.show()
    #     dlg2.exec_()
    #     # If we wanted modal, we would eliminate the dlg2.show()

    def run_add_connectors(self):
        # pass

        dlg2 = AddConnectorsDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_create_graph(self):
        dlg2 = GraphCreationDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_calibrate_gravity(self):
        dlg2 = DistributionModelsDialog(self.iface, 'calibrate')
        dlg2.show()
        dlg2.exec_()

    def run_apply_gravity(self):
        dlg2 = DistributionModelsDialog(self.iface, 'apply')
        dlg2.show()
        dlg2.exec_()

    def run_distribution_models(self):
        dlg2 = DistributionModelsDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_shortest_path(self):
        if no_binary:
            self.message_binary()
        else:
            dlg2 = ShortestPathDialog(self.iface)
            dlg2.show()
            dlg2.exec_()

    def run_dist_matrix(self):
        if no_binary:
            self.message_binary()
        else:
            dlg2 = ImpedanceMatrixDialog(self.iface)
            dlg2.show()
            dlg2.exec_()

    def run_traffic_assig(self):
        # show the dialog
        if no_binary:
            self.message_binary()
        else:
            dlg2 = TrafficAssignmentDialog(self.iface)
            dlg2.show()
            dlg2.exec_()

    def run_import_gtfs(self):
        pass

    #     dlg2 = GtfsImportDialog(self.iface)
    #     dlg2.show()
    #     dlg2.exec_()

    def run_simple_tag(self):
        # pass

        dlg2 = SimpleTagDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_lcd(self):
        # pass

        dlg2 = LeastCommonDenominatorDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_dlines(self):
        if no_binary:
            self.message_binary()
        else:
            dlg2 = DesireLinesDialog(self.iface)
            dlg2.show()
            dlg2.exec_()

    def run_bandwidth(self):
        # pass

        dlg2 = CreateBandwidthsDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_scenario_comparison(self):
        # pass

        dlg2 = CompareScenariosDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_ipf(self):
        dlg2 = DistributionModelsDialog(self.iface, 'ipf')
        dlg2.show()
        dlg2.exec_()

    def message_binary(self):
        pass
    #     qgis.utils.iface.messageBar().pushMessage("Binary Error: ",
    #                                               "Please download it from the repository using the downloader from the menu",
    #                                               level=3)

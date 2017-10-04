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
 Updated:    2017-10-02
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

# Import the PyQt and QGIS libraries
# noinspection PyUnresolvedReferences
import os
import sys
import qgis
from qgis.core import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from .common_tools import ParameterDialog, logger, ReportDialog
from binary_downloader_class import BinaryDownloaderDialog
from .distribution_procedures import IpfDialog, ApplyGravityDialog, CalibrateGravityDialog, DistributionModelsDialog
from .gis import DesireLinesDialog, CreateBandwidthsDialog, LeastCommonDenominatorDialog, SimpleTagDialog, CompareScenariosDialog
from .network import NetworkPreparationDialog, AddConnectorsDialog, CreatesTranspoNetDialog
from .paths_procedures import GraphCreationDialog, TrafficAssignmentDialog, ShortestPathDialog, ImpedanceMatrixDialog
from .matrix_procedures import LoadMatrixDialog, LoadDatasetDialog, DisplayDatasetDialog, DisplayMatrixDialog
import tempfile, glob
from .aequilibrae.__version__ import version as VERSION_GRAPH

no_binary = False
old_binary = False
try:
    from aequilibrae.paths import VERSION

    # logger((VERSION, VERSION_GRAPH))
    if VERSION != VERSION_GRAPH:
        old_binary = True
except:
    no_binary = True

sys.dont_write_bytecode = True
import os.path

class AequilibraEMenu:
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
        #Removes temporary files
        self.removes_temporary_files()

        # CREATING MASTER MENU HEAD
        self.AequilibraE_menu = QMenu(QCoreApplication.translate("AequilibraE", "AequilibraE"))
        self.iface.mainWindow().menuBar().insertMenu(self.iface.firstRightStandardMenu().menuAction(),
                                                     self.AequilibraE_menu)

        # ########################################################################
        # ################# NETWORK MANIPULATION SUB-MENU  #######################

        self.network_menu = QMenu(QCoreApplication.translate("AequilibraE", "&Network Manipulation"))
        self.aequilibrae_add_submenu(self.network_menu)

        # Network preparation
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_network.png")
        self.network_prep_action = QAction(icon, u"Network Preparation", self.iface.mainWindow())
        QObject.connect(self.network_prep_action, SIGNAL("triggered()"), self.run_net_prep)
        self.network_menu.addAction(self.network_prep_action)

        # Adding Connectors
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_network.png")
        self.add_connectors_action = QAction(icon, u"Adding Connectors", self.iface.mainWindow())
        QObject.connect(self.add_connectors_action, SIGNAL("triggered()"), self.run_add_connectors)
        self.network_menu.addAction(self.add_connectors_action)

        # Creating TranspoNet
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_network.png")
        self.create_transponet_action = QAction(icon, u"Create TranspoNet", self.iface.mainWindow())
        QObject.connect(self.create_transponet_action, SIGNAL("triggered()"), self.run_create_transponet)
        self.network_menu.addAction(self.create_transponet_action)

        # ########################################################################
        # #################  MATRIX MANIPULATION SUB-MENU  #######################

        self.matrix_menu = QMenu(QCoreApplication.translate("AequilibraE", "&Data"))
        self.aequilibrae_add_submenu(self.matrix_menu)

        # Loading matrices
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_matrices.png")
        self.load_matrix_action = QAction(icon, u"Import matrices", self.iface.mainWindow())
        QObject.connect(self.load_matrix_action, SIGNAL("triggered()"), self.run_load_matrices)
        self.matrix_menu.addAction(self.load_matrix_action)

        # Displaying Matrix
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_display_dmatrix.png")
        self.display_matrix_action = QAction(icon, u"Display matrix", self.iface.mainWindow())
        QObject.connect(self.display_matrix_action, SIGNAL("triggered()"), self.run_display_matrix)
        self.matrix_menu.addAction(self.display_matrix_action)

        # Loading Database
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_dataset.png")
        self.load_database_action = QAction(icon, u"Import dataset", self.iface.mainWindow())
        QObject.connect(self.load_database_action, SIGNAL("triggered()"), self.run_load_database)
        self.matrix_menu.addAction(self.load_database_action)

        # Displaying Database
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_display_dataset.png")
        self.display_database_action = QAction(icon, u"Display dataset", self.iface.mainWindow())
        QObject.connect(self.display_database_action, SIGNAL("triggered()"), self.run_display_dataset)
        self.matrix_menu.addAction(self.display_database_action)

        # # ########################################################################
        # # ##################  TRIP DISTRIBUTION SUB-MENU  ########################

        self.trip_distribution_menu = QMenu(QCoreApplication.translate("AequilibraE", "&Trip Distribution"))
        self.aequilibrae_add_submenu(self.trip_distribution_menu)

        # # IPF
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_ipf.png")
        self.ipf_action = QAction(icon, u"Iterative proportional fitting", self.iface.mainWindow())
        QObject.connect(self.ipf_action, SIGNAL("triggered()"), self.run_ipf)
        self.trip_distribution_menu.addAction(self.ipf_action)

        # # Apply Gravity
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_apply_gravity.png")
        self.apply_gravity_action = QAction(icon, u"Apply Gravity Model", self.iface.mainWindow())
        QObject.connect(self.apply_gravity_action, SIGNAL("triggered()"), self.run_apply_gravity)
        self.trip_distribution_menu.addAction(self.apply_gravity_action)

        # # Calibrate Gravity
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_calibrate_gravity.png")
        self.calibrate_gravity_action = QAction(icon, u"Calibrate Gravity Model", self.iface.mainWindow())
        QObject.connect(self.calibrate_gravity_action, SIGNAL("triggered()"), self.run_calibrate_gravity)
        self.trip_distribution_menu.addAction(self.calibrate_gravity_action)

        # Trip Distribution
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_distribution.png")
        self.trip_distr_action = QAction(icon, u"Trip Distribution", self.iface.mainWindow())
        QObject.connect(self.trip_distr_action, SIGNAL("triggered()"), self.run_distribution_models)
        self.trip_distribution_menu.addAction(self.trip_distr_action)

        # ########################################################################
        # ###################  PATH COMPUTATION SUB-MENU   #######################

        self.assignment_menu = QMenu(QCoreApplication.translate("AequilibraE", "&Paths and assignment"))
        self.aequilibrae_add_submenu(self.assignment_menu)

        # MATRIX HOLDER
        # icon = QIcon(os.path.dirname(__file__) + "/icons/icon_matrices.png")
        #    self.matrix_holder_action = QAction(icon,u"Matrices holder", self.iface.mainWindow())
        #    QObject.connect(self.matrix_holder_action, SIGNAL("triggered()"),self.run_matrix_holder)
        #    self.assignment_menu.addAction(self.matrix_holder_action)

        # Graph generation
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_graph_creation.png")
        self.graph_creation_action = QAction(icon, u"Create the graph", self.iface.mainWindow())
        QObject.connect(self.graph_creation_action, SIGNAL("triggered()"), self.run_create_graph)
        self.assignment_menu.addAction(self.graph_creation_action)

        # Shortest path computation
        icon = QIcon(os.path.dirname(__file__) + "/icons/single_shortest_path.png")
        self.shortest_path_action = QAction(icon, u"Shortest path", self.iface.mainWindow())
        QObject.connect(self.shortest_path_action, SIGNAL("triggered()"), self.run_shortest_path)
        self.assignment_menu.addAction(self.shortest_path_action)

        # Distance matrix generation
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_dist_matrix.png")
        self.dist_matrix_action = QAction(icon, u"Impedance matrix", self.iface.mainWindow())
        QObject.connect(self.dist_matrix_action, SIGNAL("triggered()"), self.run_dist_matrix)
        self.assignment_menu.addAction(self.dist_matrix_action)

        # Traffic Assignment
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_assignment.png")
        self.traffic_assignment_action = QAction(icon, u"Traffic Assignment", self.iface.mainWindow())
        QObject.connect(self.traffic_assignment_action, SIGNAL("triggered()"), self.run_traffic_assig)
        self.assignment_menu.addAction(self.traffic_assignment_action)
        #########################################################################

        # ########################################################################
        # #################        GIS TOOLS SUB-MENU    #########################
        self.gis_tools_menu = QMenu(QCoreApplication.translate("AequilibraE", "&GIS tools"))
        self.aequilibrae_add_submenu(self.gis_tools_menu)

        # # Node to area aggregation
        # icon = QIcon(os.path.dirname(__file__) + "/icons/icon_node_to_area.png")
        # self.node_to_area_action = QAction(icon, u"Aggregation: Node to Area", self.iface.mainWindow())
        # QObject.connect(self.node_to_area_action, SIGNAL("triggered()"), self.run_node_to_area)
        # self.gis_tools_menu.addAction(self.node_to_area_action)

        # Simple TAG
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_simple_tag.png")
        self.simple_tag_action = QAction(icon, u"Simple TAG", self.iface.mainWindow())
        QObject.connect(self.simple_tag_action, SIGNAL("triggered()"), self.run_simple_tag)
        self.gis_tools_menu.addAction(self.simple_tag_action)

        # Lowest common denominator
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_lcd.png")
        self.lcd_action = QAction(icon, u"Lowest common denominator", self.iface.mainWindow())
        QObject.connect(self.lcd_action, SIGNAL("triggered()"), self.run_lcd)
        self.gis_tools_menu.addAction(self.lcd_action)

        # Desire lines
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_desire_lines.png")
        self.dlines_action = QAction(icon, u"Desire Lines", self.iface.mainWindow())
        QObject.connect(self.dlines_action, SIGNAL("triggered()"), self.run_dlines)
        self.gis_tools_menu.addAction(self.dlines_action)

        # Bandwidths
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_bandwidths.png")
        self.bandwidth_action = QAction(icon, u"Stacked Bandwidth", self.iface.mainWindow())
        QObject.connect(self.bandwidth_action, SIGNAL("triggered()"), self.run_bandwidth)
        self.gis_tools_menu.addAction(self.bandwidth_action)

        # Scenario comparison
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_scenario_comparison.png")
        self.scenario_comparison_action = QAction(icon, u"Scenario Comparison", self.iface.mainWindow())
        QObject.connect(self.scenario_comparison_action, SIGNAL("triggered()"), self.run_scenario_comparison)
        self.gis_tools_menu.addAction(self.scenario_comparison_action)

        # ########################################################################
        # #################          LOOSE STUFF         #########################

        # Change parameters
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_parameters.png")
        self.parameters_action = QAction(icon, u"Parameters", self.iface.mainWindow())
        QObject.connect(self.parameters_action, SIGNAL("triggered()"), self.run_change_parameters)
        self.AequilibraE_menu.addAction(self.parameters_action)

        # Download binaries
        if no_binary:
            icon = QIcon(os.path.dirname(__file__) + "/icons/icon_binaries.png")
            self.binary_action = QAction(icon, u"Download binaries", self.iface.mainWindow())
            QObject.connect(self.binary_action, SIGNAL("triggered()"), self.run_binary_donwload)
            self.AequilibraE_menu.addAction(self.binary_action)


        if old_binary:
            report = ['You have an old version of the AequilibraE binaries']
            report.append('To fix this issue, please do the following:')
            report.append('     1. Uninstall AequilibraE')
            report.append('     2. Re-install AequilibraE from the official repository')
            report.append('     3. Download the new binaries from the Menu Aequilibrae-Download Binaries')
            report.append('     4. Re-start QGIS')
            dlg2 = ReportDialog(self.iface, report)
            dlg2.show()
            dlg2.exec_()
    #########################################################################

    def unload(self):
        self.removes_temporary_files()

        # unloads the add-on
        if self.AequilibraE_menu is not None:
            self.iface.mainWindow().menuBar().removeAction(self.AequilibraE_menu.menuAction())
        else:
            self.iface.removePluginMenu("&AequilibraE", self.network_menu.menuAction())
            self.iface.removePluginMenu("&AequilibraE", self.assignment_menu.menuAction())
            self.iface.removePluginMenu("&AequilibraE", self.trip_distribution_menu.menuAction())
            self.iface.removePluginMenu("&AequilibraE", self.gis_tools_menu.menuAction())

    def removes_temporary_files(self):
        # Removes all the temporary files from previous uses
        p = tempfile.gettempdir() + '/aequilibrae_*'
        for f in glob.glob(p):
            try:
                os.unlink(f)
            except:
                pass

    def run_change_parameters(self):
        dlg2 = ParameterDialog(self.iface)
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

    def run_display_dataset(self):
        dlg2 = DisplayDatasetDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_display_matrix(self):
        dlg2 = DisplayMatrixDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_binary_donwload(self):
        dlg2 = BinaryDownloaderDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    # run method that calls the network preparation section of the code
    def run_net_prep(self):
        dlg2 = NetworkPreparationDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        # If we wanted modal, we would eliminate the dlg2.show()

    # run method that calls the network preparation section of the code
    def run_create_transponet(self):
        dlg2 = CreatesTranspoNetDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        # If we wanted modal, we would eliminate the dlg2.show()

    def run_add_connectors(self):
        dlg2 = AddConnectorsDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_create_graph(self):
        dlg2 = GraphCreationDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_calibrate_gravity(self):
        dlg2 = CalibrateGravityDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_apply_gravity(self):
        dlg2 = ApplyGravityDialog(self.iface)
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

    def run_simple_tag(self):
        dlg2 = SimpleTagDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_lcd(self):
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
        dlg2 = CreateBandwidthsDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_scenario_comparison(self):
        dlg2 = CompareScenariosDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_ipf(self):
        dlg2 = IpfDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def message_binary(self):
        qgis.utils.iface.messageBar().pushMessage("Binary Error: ",
                                                  "Please download it from the repository using the downloader from the menu",
                                                  level=3)
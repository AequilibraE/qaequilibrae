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
import tempfile
import glob
from qgis.PyQt.QtWidgets import QWidget, QDockWidget, QListWidget, QListWidgetItem, QAbstractItemView, QAction, \
    QVBoxLayout, QToolBar, QToolButton, QMenu, QPushButton, QTabWidget, QLabel
import qgis
from qgis.core import QgsWkbTypes, QgsAnnotationManager, QgsProject, QgsGeometry, QgsRectangle, QgsTextAnnotation
from qgis.gui import QgsMapTool, QgsRubberBand

sys.dont_write_bytecode = True
import os.path

from qgis.PyQt import QtWidgets

# This is how QtCore and QtGui imports change
from qgis.PyQt.QtCore import *

# from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *

from .common_tools import ParameterDialog, GetOutputFileName

from .common_tools import AboutDialog
from .common_tools.auxiliary_functions import standard_path

from .binary_downloader_class import BinaryDownloaderDialog
from .download_extra_packages_class import DownloadExtraPackages
from .distribution_procedures import DistributionModelsDialog

from .gis import CompareScenariosDialog
from .gis import CreateBandwidthsDialog
from .gis import LeastCommonDenominatorDialog
from .gis import SimpleTagDialog

from .network import NetworkPreparationDialog
from .network import AddConnectorsDialog

from .matrix_procedures import LoadMatrixDialog
from .matrix_procedures import LoadDatasetDialog
from .matrix_procedures import DisplayAequilibraEFormatsDialog

# from .matrix_procedures import MatrixManipulationDialog

from .public_transport_procedures import GtfsImportDialog

from .project_procedures import ProjectFromOSMDialog

# Procedures that depend on AequilibraE
no_binary = False
try:
    from .aequilibrae.aequilibrae.paths import allOrNothing
except ImportError:
    no_binary = True

from .aequilibrae.aequilibrae.project import Project

if not no_binary:
    from .gis import DesireLinesDialog
    from .project_procedures import CreatesTranspoNetDialog
    from .paths_procedures import GraphCreationDialog
    from .paths_procedures import TrafficAssignmentDialog
    from .paths_procedures import ShortestPathDialog
    from .paths_procedures import ImpedanceMatrixDialog

extra_packages = True
try:
    import openmatrix as omx
except ImportError:
    extra_packages = False


class AequilibraEMenu:

    def __init__(self, iface):

        self.translator = None
        self.iface = iface
        self.project = None  # type: Project

        self.dock = QDockWidget(self.trlt('AequilibraE'))
        self.manager = QWidget()

        # The self.toolbar will hold everything
        self.toolbar = QToolBar()
        self.toolbar.setOrientation(2)

        # # ########################################################################
        # # #######################   PROJECT SUB-MENU   ############################

        projectMenu = QMenu()
        self.open_project_action = QAction(self.trlt('Open Project'), self.manager)
        self.open_project_action.triggered.connect(self.run_load_project)
        projectMenu.addAction(self.open_project_action)

        self.project_from_osm_action = QAction(self.trlt('Create project from OSM'), self.manager)
        self.project_from_osm_action.triggered.connect(self.run_project_from_osm)
        projectMenu.addAction(self.project_from_osm_action)

        self.create_transponet_action = QAction(self.trlt('Create Project from layers'), self.manager)
        self.create_transponet_action.triggered.connect(self.run_create_transponet)
        projectMenu.addAction(self.create_transponet_action)

        projectButton = QToolButton()
        projectButton.setText(self.trlt('Project'))
        projectButton.setPopupMode(2)
        projectButton.setMenu(projectMenu)

        self.toolbar.addWidget(projectButton)

        # # ########################################################################
        # # ################# NETWORK MANIPULATION SUB-MENU  #######################

        netMenu = QMenu()
        self.action_netPrep = QAction(self.trlt('Network Preparation'), self.manager)
        self.action_netPrep.triggered.connect(self.run_net_prep)
        netMenu.addAction(self.action_netPrep)

        self.add_connectors_action = QAction(self.trlt('Add centroid connectors'), self.manager)
        self.add_connectors_action.triggered.connect(self.run_add_connectors)
        netMenu.addAction(self.add_connectors_action)

        netbutton = QToolButton()
        netbutton.setText(self.trlt('Network Manipulation'))
        netbutton.setMenu(netMenu)
        netbutton.setPopupMode(2)

        self.toolbar.addWidget(netbutton)
        # # ########################################################################
        # # ####################  DATA UTILITIES SUB-MENU  #########################

        dataMenu = QMenu()
        self.display_custom_formats_action = QAction(self.trlt('Display AequilibraE formats'), self.manager)
        self.display_custom_formats_action.triggered.connect(self.run_display_aequilibrae_formats)
        dataMenu.addAction(self.display_custom_formats_action)

        self.load_matrix_action = QAction(self.trlt('Import matrices'), self.manager)
        self.load_matrix_action.triggered.connect(self.run_load_matrices)
        dataMenu.addAction(self.load_matrix_action)

        self.load_database_action = QAction(self.trlt('Import dataset'), self.manager)
        self.load_database_action.triggered.connect(self.run_load_database)
        dataMenu.addAction(self.load_database_action)

        databutton = QToolButton()
        databutton.setText(self.trlt('Data'))
        databutton.setPopupMode(2)
        databutton.setMenu(dataMenu)

        self.toolbar.addWidget(databutton)

        # # # ########################################################################
        # # # ##################  TRIP DISTRIBUTION SUB-MENU  ########################

        distMenu = QMenu()
        self.ipf_action = QAction(self.trlt('Iterative proportional fitting'), self.manager)
        self.ipf_action.triggered.connect(self.run_ipf)
        distMenu.addAction(self.ipf_action)

        self.apply_gravity_action = QAction(self.trlt('Apply Gravity Model'), self.manager)
        self.apply_gravity_action.triggered.connect(self.run_apply_gravity)
        distMenu.addAction(self.apply_gravity_action)

        self.calibrate_gravity_action = QAction(self.trlt('Calibrate Gravity Model'), self.manager)
        self.calibrate_gravity_action.triggered.connect(self.run_calibrate_gravity)
        distMenu.addAction(self.calibrate_gravity_action)

        self.trip_distr_action = QAction(self.trlt('Trip Distribution'), self.manager)
        self.trip_distr_action.triggered.connect(self.run_distribution_models)
        distMenu.addAction(self.trip_distr_action)

        distributionButton = QToolButton()
        distributionButton.setText(self.trlt('Trip Distribution'))
        distributionButton.setPopupMode(2)
        distributionButton.setMenu(distMenu)

        self.toolbar.addWidget(distributionButton)

        # # ########################################################################
        # # ###################  PATH COMPUTATION SUB-MENU   #######################
        pathMenu = QMenu()
        self.graph_creation_action = QAction(self.trlt('Create graph'), self.manager)
        self.graph_creation_action.triggered.connect(self.run_create_graph)
        pathMenu.addAction(self.graph_creation_action)

        self.shortest_path_action = QAction(self.trlt('Shortest path'), self.manager)
        self.shortest_path_action.triggered.connect(self.run_shortest_path)
        pathMenu.addAction(self.shortest_path_action)

        self.dist_matrix_action = QAction(self.trlt('Impedance matrix'), self.manager)
        self.dist_matrix_action.triggered.connect(self.run_dist_matrix)
        pathMenu.addAction(self.dist_matrix_action)

        self.traffic_assignment_action = QAction(self.trlt('Traffic Assignment'), self.manager)
        self.traffic_assignment_action.triggered.connect(self.run_traffic_assig)
        pathMenu.addAction(self.traffic_assignment_action)

        pathButton = QToolButton()
        pathButton.setText(self.trlt('Paths and assignment'))
        pathButton.setPopupMode(2)
        pathButton.setMenu(pathMenu)

        self.toolbar.addWidget(pathButton)

        # # ########################################################################
        # # #######################  TRANSIT SUB-MENU   ###########################
        transitMenu = QMenu()
        self.gtfs_import_action = QAction(self.trlt('Convert GTFS to SpatiaLite'), self.manager)
        self.gtfs_import_action.triggered.connect(self.run_import_gtfs)
        transitMenu.addAction(self.gtfs_import_action)

        transitButton = QToolButton()
        transitButton.setText(self.trlt('Public Transport'))
        transitButton.setPopupMode(2)
        transitButton.setMenu(transitMenu)

        self.toolbar.addWidget(transitButton)

        # ########################################################################
        # #################        GIS TOOLS SUB-MENU    #########################

        gisMenu = QMenu()
        self.simple_tag_action = QAction(self.trlt('Simple tag'), self.manager)
        self.simple_tag_action.triggered.connect(self.run_simple_tag)
        gisMenu.addAction(self.simple_tag_action)

        self.lcd_action = QAction(self.trlt('Lowest common denominator'), self.manager)
        self.lcd_action.triggered.connect(self.run_lcd)
        gisMenu.addAction(self.lcd_action)

        self.dlines_action = QAction(self.trlt('Desire Lines'), self.manager)
        self.dlines_action.triggered.connect(self.run_dlines)
        gisMenu.addAction(self.dlines_action)

        self.bandwidth_action = QAction(self.trlt('Stacked Bandwidth'), self.manager)
        self.bandwidth_action.triggered.connect(self.run_bandwidth)
        gisMenu.addAction(self.bandwidth_action)

        self.scenario_comparison_action = QAction(self.trlt('Scenario Comparison'), self.manager)
        self.scenario_comparison_action.triggered.connect(self.run_scenario_comparison)
        gisMenu.addAction(self.scenario_comparison_action)

        gisButton = QToolButton()
        gisButton.setText(self.trlt('GIS'))
        gisButton.setPopupMode(2)
        gisButton.setMenu(gisMenu)

        self.toolbar.addWidget(gisButton)

        # ########################################################################
        # #################          LOOSE STUFF         #########################

        parametersButton = QToolButton()
        parametersButton.setText(self.trlt('Parameters'))
        parametersButton.clicked.connect(self.run_change_parameters)
        self.toolbar.addWidget(parametersButton)

        aboutButton = QToolButton()
        aboutButton.setText(self.trlt('About'))
        aboutButton.clicked.connect(self.run_about)
        self.toolbar.addWidget(aboutButton)

        if no_binary:
            binariesButton = QToolButton()
            binariesButton.setText(self.trlt('Download binaries'))
            binariesButton.clicked.connect(self.run_binary_download)
            self.toolbar.addWidget(binariesButton)

        if not extra_packages:
            xtrapkgButton = QToolButton()
            xtrapkgButton.setText(self.trlt('Install extra packages'))
            xtrapkgButton.clicked.connect(self.install_extra_packages)
            self.toolbar.addWidget(xtrapkgButton)

        # ########################################################################
        # #################        PROJECT MANAGER       #########################

        self.projectManager = QTabWidget()
        self.toolbar.addWidget(self.projectManager)

        # # # ########################################################################
        self.toolbar.setIconSize(QSize(16, 16))

        p1_vertical = QVBoxLayout()
        p1_vertical.setContentsMargins(0, 0, 0, 0)
        p1_vertical.addWidget(self.toolbar)
        self.manager.setLayout(p1_vertical)

        self.dock.setWidget(self.manager)
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)

    def unload(self):
        del self.dock

    def trlt(self, message):
        # In the near future, we will use this function to automatically translate the AequilibraE menu
        # To any language we can get people to translate it to
        # return QCoreApplication.translate('AequilibraE', message)
        return message

    def initGui(self):
        pass

    def removes_temporary_files(self):
        # pass
        # Removes all the temporary files from previous uses
        p = tempfile.gettempdir() + "/aequilibrae_*"
        for f in glob.glob(p):
            try:
                os.unlink(f)
            except:
                pass

    def run_load_project(self):
        formats = ["AequilibraE Project(*.sqlite)"]
        path, dtype = GetOutputFileName(QtWidgets.QDialog(), "AequilibraE Project", formats, ".sqlite",
                                        standard_path(), )

        # Cleans the project descriptor
        tab_count = 1
        for i in range(tab_count):
            self.projectManager.removeTab(i)

        if dtype is not None:
            self.project = Project(path)
            self.project.conn = qgis.utils.spatialite_connect(path)

            descr = QWidget()
            descrlayout = QVBoxLayout()
            # We create a tab with the main description of the project
            p1 = QLabel('Project: {}'.format(path))
            descrlayout.addWidget(p1)

            p2 = QLabel('Modes: {}'.format(', '.join(self.project.network.modes())))
            descrlayout.addWidget(p2)

            p3 = QLabel('Total Links: {:,}'.format(self.project.network.count_links()))
            descrlayout.addWidget(p3)

            p4 = QLabel('Total Nodes: {:,}'.format(self.project.network.count_nodes()))
            descrlayout.addWidget(p4)

            descr.setLayout(descrlayout)
            self.projectManager.addTab(descr, "Project")

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

    def install_extra_packages(self):
        dlg2 = DownloadExtraPackages(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_binary_download(self):
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
        if no_binary:
            self.message_binary()
        else:
            dlg2 = CreatesTranspoNetDialog(self.iface)
            dlg2.show()
            dlg2.exec_()
        # If we wanted modal, we would eliminate the dlg2.show()

    def run_add_connectors(self):
        dlg2 = AddConnectorsDialog(self.iface, self.project)
        dlg2.show()
        dlg2.exec_()

    def run_create_graph(self):
        if no_binary:
            self.message_binary()
        else:
            dlg2 = GraphCreationDialog(self.iface)
            dlg2.show()
            dlg2.exec_()

    def run_calibrate_gravity(self):
        dlg2 = DistributionModelsDialog(self.iface, "calibrate")
        dlg2.show()
        dlg2.exec_()

    def run_apply_gravity(self):
        dlg2 = DistributionModelsDialog(self.iface, "apply")
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
        if no_binary:
            self.message_binary()
        else:
            dlg2 = TrafficAssignmentDialog(self.iface)
            dlg2.show()
            dlg2.exec_()

    def run_import_gtfs(self):
        dlg2 = GtfsImportDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_project_from_osm(self):
        dlg2 = ProjectFromOSMDialog(self.iface)
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
        dlg2 = DistributionModelsDialog(self.iface, "ipf")
        dlg2.show()
        dlg2.exec_()

    def message_binary(self):
        qgis.utils.iface.messageBar().pushMessage(
            "Binary Error: ", "Please download it from the repository using the downloader from the menu", level=3
        )

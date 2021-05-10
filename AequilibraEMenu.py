import os
import sys
import tempfile
import glob
import importlib.util as iutil
from qgis.PyQt.QtWidgets import QWidget, QDockWidget, QListWidget, QListWidgetItem, QAbstractItemView, QAction, \
    QVBoxLayout, QToolBar, QToolButton, QMenu, QPushButton, QTabWidget, QLabel, QCheckBox
import qgis
from qgis.core import QgsWkbTypes, QgsAnnotationManager, QgsProject, QgsGeometry, QgsRectangle, QgsTextAnnotation, QgsApplication
from qgis.gui import QgsMapTool, QgsRubberBand

from .processing_provider.provider import Provider

sys.dont_write_bytecode = True
import subprocess
import webbrowser

from qgis.PyQt import QtWidgets
from qgis.core import QgsDataSourceUri, QgsVectorLayer
# This is how QtCore and QtGui imports change
from qgis.PyQt.QtCore import *

# from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *

from .common_tools import ParameterDialog, GetOutputFileName, LogDialog

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

from .public_transport_procedures import GtfsImportDialog

from .project_procedures import ProjectFromOSMDialog
from warnings import warn

no_binary = False
try:
    from .aequilibrae.aequilibrae.paths import allOrNothing
except ImportError as e:
    no_binary = True
    warn(f'AequilibraE binaries are not available {e.args}')

from aequilibrae.project import Project

if not no_binary:
    from .gis.desire_lines_dialog import DesireLinesDialog
    from .project_procedures import CreatesTranspoNetDialog
    from .paths_procedures import TrafficAssignmentDialog
    from .paths_procedures import ShortestPathDialog
    from .paths_procedures import ImpedanceMatrixDialog

extra_packages = True
# Checks if we can display OMX
spec = iutil.find_spec("openmatrix")
has_omx = spec is not None
if not has_omx:
    extra_packages = False

gtools = True
spec = iutil.find_spec("openmatrix")
has_ortools = spec is not None

if has_ortools:
    from .routing_procedures import TSPDialog


class AequilibraEMenu:

    def __init__(self, iface):

        self.translator = None
        self.iface = iface
        self.project = None  # type: Project
        self.link_layer = None  # type: QgsVectorLayer
        self.node_layer = None  # type: QgsVectorLayer
        self.provider = None

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

        distributionButton = QToolButton()
        distributionButton.setText(self.trlt('Trip Distribution'))
        distributionButton.clicked.connect(self.run_distribution_models)
        self.toolbar.addWidget(distributionButton)

        # # ########################################################################
        # # ###################  PATH COMPUTATION SUB-MENU   #######################
        pathMenu = QMenu()

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
        # # #######################   ROUTING SUB-MENU   ###########################
        if has_ortools:
            routingMenu = QMenu()
            self.tsp_action = QAction(self.trlt('Travelling Salesman Problem'), self.manager)
            self.tsp_action.triggered.connect(self.run_tsp)
            routingMenu.addAction(self.tsp_action)

            routingButton = QToolButton()
            routingButton.setText(self.trlt('Routing'))
            routingButton.setPopupMode(2)
            routingButton.setMenu(routingMenu)

            self.toolbar.addWidget(routingButton)

        # # ########################################################################
        # # #######################   TRANSIT SUB-MENU   ###########################
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

        logButton = QToolButton()
        logButton.setText(self.trlt('logfile'))
        logButton.clicked.connect(self.run_log)
        self.toolbar.addWidget(logButton)

        helpButton = QToolButton()
        helpButton.setText(self.trlt('Help'))
        helpButton.clicked.connect(self.run_help)
        self.toolbar.addWidget(helpButton)

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

        self.showing = QCheckBox()
        self.showing.setText('Show project info')
        self.showing.setChecked(True)
        self.toolbar.addWidget(self.showing)

        self.showing.toggled.connect(self.hide_info_pannel)
        self.projectManager = QTabWidget()
        self.toolbar.addWidget(self.projectManager)

        # # # ########################################################################
        self.tabContents = []
        self.toolbar.setIconSize(QSize(16, 16))

        p1_vertical = QVBoxLayout()
        p1_vertical.setContentsMargins(0, 0, 0, 0)
        p1_vertical.addWidget(self.toolbar)
        self.manager.setLayout(p1_vertical)

        self.dock.setWidget(self.manager)
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)

    def run_help(self):
        url = 'http://aequilibrae.com/qgis'
        if sys.platform == 'darwin':  # in case of OS X
            subprocess.Popen(['open', url])
        else:
            webbrowser.open_new_tab(url)

    def run_log(self):
        dlg2 = LogDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def unload(self):
        del self.dock
        try:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        except:
            pass

    def trlt(self, message):
        # In the near future, we will use this function to automatically translate the AequilibraE menu
        # To any language we can get people to translate it to
        # return QCoreApplication.translate('AequilibraE', message)
        return message

    def initProcessing(self):
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)    

    def initGui(self):
        self.initProcessing()
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

    def hide_info_pannel(self):
        if len(self.tabContents) > 0:
            if self.showing.isChecked():
                for v in self.tabContents:
                    self.projectManager.addTab(v[0], v[1])
            else:
                tab_count = 1
                for i in range(tab_count):
                    self.projectManager.removeTab(i)

    def run_load_project(self):
        formats = ["AequilibraE Project(*.sqlite)"]
        path, dtype = GetOutputFileName(QtWidgets.QDialog(), "AequilibraE Project", formats, ".sqlite",
                                        standard_path(), )

        # Cleans the project descriptor
        tab_count = 1
        for i in range(tab_count):
            self.projectManager.removeTab(i)

        if dtype is not None:
            self.contents = []
            self.showing.setVisible(True)
            self.project = Project()
            self.project.load(path)
            self.project.conn = qgis.utils.spatialite_connect(path)
            self.project.network.conn = self.project.conn

            uri = QgsDataSourceUri()
            uri.setDatabase(path)
            uri.setDataSource('', 'links', 'geometry')
            self.link_layer = QgsVectorLayer(uri.uri(), 'links', 'spatialite')
            QgsProject.instance().addMapLayer(self.link_layer)

            uri.setDataSource('', 'nodes', 'geometry')
            self.node_layer = QgsVectorLayer(uri.uri(), 'nodes', 'spatialite')
            QgsProject.instance().addMapLayer(self.node_layer)

            descr = QWidget()
            descrlayout = QVBoxLayout()
            # We create a tab with the main description of the project
            p1 = QLabel('Project: {}'.format(path))
            p2 = QLabel('Modes: {}'.format(', '.join(self.project.network.modes())))
            p3 = QLabel('Total Links: {:,}'.format(self.project.network.count_links()))
            p4 = QLabel('Total Nodes: {:,}'.format(self.project.network.count_nodes()))

            for p in [p1, p2, p3, p4]:
                descrlayout.addWidget(p)

            descr.setLayout(descrlayout)
            self.tabContents = [(descr, "Project")]
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

    def run_distribution_models(self):
        dlg2 = DistributionModelsDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_shortest_path(self):
        if no_binary:
            self.message_binary()
        else:
            if self.project is None:
                self.show_message_no_project()
            else:
                dlg2 = ShortestPathDialog(self.iface, self.project, self.link_layer, self.node_layer)
                dlg2.show()
                dlg2.exec_()

    def run_dist_matrix(self):
        if no_binary:
            self.message_binary()
        else:
            if self.project is None:
                self.show_message_no_project()
            else:
                dlg2 = ImpedanceMatrixDialog(self.iface, self.project, self.link_layer)
                dlg2.show()
                dlg2.exec_()

    def run_traffic_assig(self):
        if no_binary:
            self.message_binary()
        else:
            if self.project is None:
                self.show_message_no_project()
            else:
                dlg2 = TrafficAssignmentDialog(self.iface, self.project, self.link_layer)
                dlg2.show()
                dlg2.exec_()

    def run_tsp(self):
        if self.project is None:
            self.show_message_no_project()
        else:
            dlg2 = TSPDialog(self.iface, self.project, self.link_layer, self.node_layer)
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

    def message_binary(self):
        qgis.utils.iface.messageBar().pushMessage(
            "Binary Error: ", "Please download it from the repository using the downloader from the menu", level=3
        )

    def show_message_no_project(self):
        self.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)

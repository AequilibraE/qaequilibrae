import glob
import importlib.util as iutil
import logging
import os
import subprocess
import sys
import tempfile
import webbrowser
from functools import partial
from typing import Dict
from warnings import warn

from aequilibrae.project import Project
from aequilibrae.project.database_connection import ENVIRON_VAR

import qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt import QtCore
from qgis.PyQt.QtWidgets import QVBoxLayout, QApplication
from qgis.PyQt.QtWidgets import QWidget, QDockWidget, QAction, QMenu, QTabWidget, QCheckBox, QToolBar, QToolButton
from qgis.core import QgsDataSourceUri, QgsVectorLayer
from qgis.core import QgsProject
from .binary_downloader_class import BinaryDownloaderDialog
from .common_tools import AboutDialog
from .common_tools import ParameterDialog, LogDialog
from .download_extra_packages_class import DownloadExtraPackages
from .gis import CompareScenariosDialog
from .gis import CreateBandwidthsDialog
from .gis import LeastCommonDenominatorDialog
from .gis import SimpleTagDialog
from .matrix_procedures import LoadDatasetDialog
from .menu_actions import run_add_zones, display_aequilibrae_formats, run_show_project_data, load_matrices
from .menu_actions import run_distribution_models, run_tsp
from .menu_actions import run_load_project, project_from_osm, run_create_transponet, prepare_network, run_add_connectors
from .paths_procedures import run_shortest_path, run_dist_matrix, run_traffic_assig
from .public_transport_procedures import GtfsImportDialog

# This is how QtCore and QtGui imports change

no_binary = False
try:
    from .aequilibrae.aequilibrae.paths import allOrNothing
except ImportError as e:
    no_binary = True
    warn(f'AequilibraE binaries are not available {e.args}')

if not no_binary:
    from .gis.desire_lines_dialog import DesireLinesDialog

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

if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class AequilibraEMenu:

    def __init__(self, iface):
        # Closes AequilibraE projects eventually opened in memory
        self.logger = logging.getLogger('AequilibraEGUI')
        if ENVIRON_VAR in os.environ:
            del os.environ[ENVIRON_VAR]
        self.geo_layers_list = ['links', 'nodes', 'zones']
        self.translator = None
        self.iface = iface
        self.project = None  # type: Project
        self.layers = {}  # type: Dict[QgsVectorLayer]
        self.dock = QDockWidget(self.trlt('AequilibraE'))
        self.manager = QWidget()
        self.no_binary = no_binary

        # The self.toolbar will hold everything
        self.toolbar = QToolBar()
        self.set_font(self.toolbar)
        self.toolbar.setOrientation(2)

        self.menuActions = {'Project': [],
                            'Network Manipulation': [],
                            'Data': [],
                            'Trip Distribution': [],
                            'Paths and assignment': [],
                            'Routing': [],
                            'Public Transport': [],
                            'GIS': [],
                            'Utils': []}

        # # #######################   PROJECT SUB-MENU   ############################
        self.add_menu_action('Project', 'Open Project', partial(run_load_project, self))
        self.add_menu_action('Project', 'Create project from OSM', partial(project_from_osm, self))
        self.add_menu_action('Project', 'Create Project from layers', partial(run_create_transponet, self))
        self.add_menu_action('Project', 'Add zoning data', partial(run_add_zones, self))
        self.add_menu_action('Project', 'Close project', self.run_close_project)

        # # # ########################################################################
        # # # ################# NETWORK MANIPULATION SUB-MENU  #######################

        self.add_menu_action('Network Manipulation', 'Network Preparation', partial(prepare_network, self))
        self.add_menu_action('Network Manipulation', 'Add centroid connectors', partial(run_add_connectors, self))

        # # # ########################################################################
        # # # ####################  DATA UTILITIES SUB-MENU  #########################
        self.add_menu_action('Data', 'Display project data', partial(run_show_project_data, self))

        # # # # ########################################################################
        # # # # ##################  TRIP DISTRIBUTION SUB-MENU  ########################

        self.add_menu_action('Trip Distribution', 'Trip Distribution', partial(run_distribution_models, self))

        # # # ########################################################################
        # # # ###################  PATH COMPUTATION SUB-MENU   #######################
        #
        self.add_menu_action('Paths and assignment', 'Shortest path', partial(run_shortest_path, self))
        self.add_menu_action('Paths and assignment', 'Impedance matrix', partial(run_dist_matrix, self))
        self.add_menu_action('Paths and assignment', 'Traffic Assignment', partial(run_traffic_assig, self))

        # # # ########################################################################
        # # # #######################   ROUTING SUB-MENU   ###########################
        if has_ortools:
            self.add_menu_action('Routing', 'Travelling Salesman Problem', partial(run_tsp, self))
        else:
            _ = self.menuActions.pop('Routing')

        # # # ########################################################################
        # # # #######################   TRANSIT SUB-MENU   ###########################
        # transitMenu = QMenu()
        # self.gtfs_import_action = QAction(self.trlt('Convert GTFS to SpatiaLite'), self.manager)
        # self.gtfs_import_action.triggered.connect(self.run_import_gtfs)
        # transitMenu.addAction(self.gtfs_import_action)
        #
        # transitButton = QToolButton()
        # transitButton.setText(self.trlt('Public Transport'))
        # transitButton.setPopupMode(2)
        # transitButton.setMenu(transitMenu)
        #
        # self.toolbar.addWidget(transitButton)
        #
        # # ########################################################################
        # # #################        GIS TOOLS SUB-MENU    #########################
        #
        # gisMenu = QMenu()
        # self.simple_tag_action = QAction(self.trlt('Simple tag'), self.manager)
        # self.simple_tag_action.triggered.connect(self.run_simple_tag)
        # gisMenu.addAction(self.simple_tag_action)
        #
        # self.lcd_action = QAction(self.trlt('Lowest common denominator'), self.manager)
        # self.lcd_action.triggered.connect(self.run_lcd)
        # gisMenu.addAction(self.lcd_action)
        #
        # self.dlines_action = QAction(self.trlt('Desire Lines'), self.manager)
        # self.dlines_action.triggered.connect(self.run_dlines)
        # gisMenu.addAction(self.dlines_action)
        #
        # self.bandwidth_action = QAction(self.trlt('Stacked Bandwidth'), self.manager)
        # self.bandwidth_action.triggered.connect(self.run_bandwidth)
        # gisMenu.addAction(self.bandwidth_action)
        #
        # self.scenario_comparison_action = QAction(self.trlt('Scenario Comparison'), self.manager)
        # self.scenario_comparison_action.triggered.connect(self.run_scenario_comparison)
        # gisMenu.addAction(self.scenario_comparison_action)
        #
        # gisButton = QToolButton()
        # gisButton.setText(self.trlt('GIS'))
        # gisButton.setPopupMode(2)
        # gisButton.setMenu(gisMenu)
        #
        # self.toolbar.addWidget(gisButton)

        # # ########################################################################
        # # #################          Utils submenu         #########################
        self.add_menu_action('Data', 'Import matrices', partial(load_matrices, self))
        self.add_menu_action('Utils', 'Display Matrices and datasets', partial(display_aequilibrae_formats, self))

        self.build_menu()
        # # ########################################################################
        # # #################          LOOSE STUFF         #########################
        #
        # parametersButton = QToolButton()
        # parametersButton.setText(self.trlt('Parameters'))
        # parametersButton.clicked.connect(self.run_change_parameters)
        # self.toolbar.addWidget(parametersButton)
        #
        # aboutButton = QToolButton()
        # aboutButton.setText(self.trlt('About'))
        # aboutButton.clicked.connect(self.run_about)
        # self.toolbar.addWidget(aboutButton)
        #
        # logButton = QToolButton()
        # logButton.setText(self.trlt('logfile'))
        # logButton.clicked.connect(self.run_log)
        # self.toolbar.addWidget(logButton)
        #
        # helpButton = QToolButton()
        # helpButton.setText(self.trlt('Help'))
        # helpButton.clicked.connect(self.run_help)
        # self.toolbar.addWidget(helpButton)
        #
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

        self.projectManager = QTabWidget()
        self.toolbar.addWidget(self.projectManager)

        # # # ########################################################################
        self.tabContents = []
        self.toolbar.setIconSize(QtCore.QSize(16, 16))

        p1_vertical = QVBoxLayout()
        p1_vertical.setContentsMargins(0, 0, 0, 0)
        p1_vertical.addWidget(self.toolbar)
        self.manager.setLayout(p1_vertical)

        self.dock.setWidget(self.manager)
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        QgsProject.instance().layerRemoved.connect(self.layerRemoved)

    def add_menu_action(self, main_menu: str, text: str, function, submenu=None):
        if main_menu == 'AequilibraE':
            action = QToolButton()
            action.setText(text)
            action.clicked.connect(function)
        else:
            action = QAction(text, self.manager)
            action.triggered.connect(function)
        if submenu is None:
            self.menuActions[main_menu].append(action)
        else:
            self.menuActions[main_menu][submenu].append(action)

    def build_menu(self):
        for menu, actions in self.menuActions.items():
            if menu == 'Polaris':
                for action in actions:
                    self.toolbar.addWidget(action)
                continue
            itemMenu = QMenu()
            self.set_font(itemMenu)
            if isinstance(actions, dict):
                for submenu, mini_actions in actions.items():
                    new_sub_menu = itemMenu.addMenu(submenu)
                    self.set_font(new_sub_menu)
                    for mini_action in mini_actions:
                        new_sub_menu.addAction(mini_action)
            else:
                for action in actions:
                    itemMenu.addAction(action)
            itemButton = QToolButton()
            itemButton.setText(menu)
            itemButton.setPopupMode(2)
            itemButton.setMenu(itemMenu)

            self.toolbar.addWidget(itemButton)

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
            except Exception as e:
                self.logger.error(e.args)
                pass

    def run_close_project(self):
        if self.project is None:
            return
        self.project.close()
        self.projectManager.clear()
        self.project = None

    def layerRemoved(self, layer):
        layers_to_re_create = [key for key, val in self.layers.items() if val[1] == layer]

        # Clears the pool of layers
        self.layers = {key: val for key, val in self.layers.items() if val[1] != layer}

        # Re-creates in memory only the layer that was destroyed
        for layer_name in layers_to_re_create:
            self.create_layer_by_name(layer_name)

    def load_geo_layer(self):
        sel = self.geo_layers_table.selectedItems()
        lyr = [s.text() for s in sel][0]
        self.load_layer_by_name(lyr)

    def load_layer_by_name(self, layer_name: str):
        if layer_name.lower() not in self.layers:
            print('Layer was not found, which is weird')
            self.create_layer_by_name(layer_name)
        layer = self.layers[layer_name.lower()][0]
        QgsProject.instance().addMapLayer(layer)
        qgis.utils.iface.mapCanvas().refresh()

    def create_layer_by_name(self, layer_name: str):
        layer = self.create_loose_layer(layer_name)
        self.layers[layer_name.lower()] = [layer, layer.id()]

    def create_loose_layer(self, layer_name: str) -> QgsVectorLayer:
        uri = QgsDataSourceUri()
        uri.setDatabase(self.project.path_to_file)
        uri.setDataSource('', layer_name, 'geometry')
        layer = QgsVectorLayer(uri.uri(), layer_name, 'spatialite')
        return layer

    def run_change_parameters(self):
        dlg2 = ParameterDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_about(self):
        dlg2 = AboutDialog(self.iface)
        dlg2.show()
        dlg2.exec_()

    def run_load_database(self):
        dlg2 = LoadDatasetDialog(self.iface, single_use=False)
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

    def run_import_gtfs(self):
        dlg2 = GtfsImportDialog(self.iface)
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

    def message_project_already_open(self):
        self.iface.messageBar().pushMessage("You need to close the project currently open first", level=2, duration=10)

    def set_font(self, obj):
        f = obj.font()
        f.setPointSize(11)
        obj.setFont(f)

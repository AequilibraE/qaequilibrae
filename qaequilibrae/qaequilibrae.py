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

import qgis

from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QVBoxLayout, QApplication
from qgis.PyQt.QtWidgets import QWidget, QDockWidget, QAction, QMenu, QTabWidget, QCheckBox, QToolBar, QToolButton
from qgis.core import QgsDataSourceUri, QgsVectorLayer
from qgis.core import QgsProject, QgsSettings
from qgis.PyQt.QtCore import QTranslator

from qaequilibrae.modules.menu_actions import load_matrices, run_add_connectors, run_stacked_bandwidths, run_tag
from qaequilibrae.modules.menu_actions import run_add_zones, display_aequilibrae_formats, run_show_project_data
from qaequilibrae.modules.menu_actions import run_desire_lines, run_scenario_comparison, run_lcd, run_import_gtfs
from qaequilibrae.modules.menu_actions import run_distribution_models, run_tsp, run_change_parameters, prepare_network, run_about
from qaequilibrae.modules.menu_actions import run_load_project, project_from_osm, run_create_transponet, show_log
from qaequilibrae.modules.paths_procedures import run_shortest_path, run_dist_matrix, run_traffic_assig

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages"))
    from aequilibrae.project import Project
except:
    from qgis.PyQt.QtWidgets import QMessageBox

    if QMessageBox.question(None, "AequilibraE and other dependencies are not not installed",
                            "Do you want us to install these missing python packages? \r\n"
                            "QGIS will be non-responsive for a couple of minutes.",
                            QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
        from qaequilibrae.download_extra_packages_class import download_all

        result = download_all().install()
        if "ERROR" in "".join([str(x).upper() for x in result]):
            QMessageBox.information(None, "Information", "Errors may have happened during installation."
                                                         "Please inspect the messages on your General Log message tab")
        else:
            QMessageBox.information(None, "Information", "You will probably need to restart QGIS to make it work")
    else:
        QMessageBox.information(None,
                                "Information",
                                "Without installing the packages, the plugin will be mostly non-functional")

if hasattr(Qt, "AA_EnableHighDpiScaling"):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

if hasattr(Qt, "AA_UseHighDpiPixmaps"):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class AequilibraEMenu:
    def __init__(self, iface):
        # Closes AequilibraE projects eventually opened in memory
        self.logger = logging.getLogger("AequilibraEGUI")
        self.geo_layers_list = ["links", "nodes", "zones"]
        # translator = None
        self.iface = iface
        self.project = None  # type: Project
        self.matrices = {}
        self.layers = {}  # type: Dict[QgsVectorLayer]
        self.dock = QDockWidget(self.trlt("AequilibraE"))
        self.manager = QWidget()

        # The self.toolbar will hold everything
        self.toolbar = QToolBar()
        self.set_font(self.toolbar)
        self.toolbar.setOrientation(2)
        
        if QtCore.QSettings().value("locale/overrideFlag", type=bool):
            loc = QtCore.QSettings().value('locale/userLocale')
        else:
            loc = QtCore.QLocale.system().name()
        loc = loc if len(loc) == 5 else loc[:2]
    
        locale_path = '{}/i18n/qaequilibrae_{}.qm'.format(os.path.dirname(__file__), loc)

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QtCore.QCoreApplication.installTranslator(self.translator)

        self.menuActions = {
            self.tr("Project"): [],
            self.tr("Network Manipulation"): [],
            self.tr("Data"): [],
            self.tr("Trip Distribution"): [],
            self.tr("Paths and assignment"): [],
            self.tr("Routing"): [],
            self.tr("Public Transport"): [],
            "GIS": [],
            self.tr("Utils"): [],
            "AequilibraE": [],
        }

        # # #######################   PROJECT SUB-MENU   ############################
        self.add_menu_action("Project", self.tr("Open Project"), partial(run_load_project, self))
        self.add_menu_action("Project", self.tr("Create project from OSM"), partial(project_from_osm, self))
        self.add_menu_action("Project", self.tr("Create Project from layers"), partial(run_create_transponet, self))
        self.add_menu_action("Project", self.tr("Add zoning data"), partial(run_add_zones, self))
        self.add_menu_action("Project", self.tr("Parameters"), partial(run_change_parameters, self))
        self.add_menu_action("Project", self.tr("logfile"), partial(show_log, self))
        self.add_menu_action("Project", self.tr("Close project"), self.run_close_project)

        # # # ########################################################################
        # # # ################# NETWORK MANIPULATION SUB-MENU  #######################

        self.add_menu_action("Network Manipulation", self.tr("Network Preparation"), partial(prepare_network, self))
        self.add_menu_action("Network Manipulation", self.tr("Add centroid connectors"), partial(run_add_connectors, self))

        # # # ########################################################################
        # # # ####################  DATA UTILITIES SUB-MENU  #########################
        self.add_menu_action("Data", self.tr("Display project data"), partial(run_show_project_data, self))

        # # # # ########################################################################
        # # # # ##################  TRIP DISTRIBUTION SUB-MENU  ########################

        self.add_menu_action("Trip Distribution", self.tr("Trip Distribution"), partial(run_distribution_models, self))

        # # # ########################################################################
        # # # ###################  PATH COMPUTATION SUB-MENU   #######################
        #
        self.add_menu_action("Paths and assignment", self.tr("Shortest path"), partial(run_shortest_path, self))
        self.add_menu_action("Paths and assignment", self.tr("Impedance matrix"), partial(run_dist_matrix, self))
        self.add_menu_action("Paths and assignment", self.tr("Traffic Assignment"), partial(run_traffic_assig, self))

        # # # ########################################################################
        # # # #######################   ROUTING SUB-MENU   ###########################
        self.add_menu_action("Routing", self.tr("Travelling Salesman Problem"), partial(run_tsp, self))

        # # # ########################################################################
        # # # #######################   TRANSIT SUB-MENU   ###########################
        self.add_menu_action('Public Transport', self.tr('Import GTFS'), partial(run_import_gtfs, self))

        # # ########################################################################
        # # #################        GIS TOOLS SUB-MENU    #########################
        self.add_menu_action("GIS", self.tr("Desire Lines"), partial(run_desire_lines, self))
        self.add_menu_action("GIS", self.tr("Stacked Bandwidth"), partial(run_stacked_bandwidths, self))
        self.add_menu_action("GIS", self.tr("Scenario Comparison"), partial(run_scenario_comparison, self))
        self.add_menu_action("GIS", self.tr("Lowest common denominator"), partial(run_lcd, self))
        self.add_menu_action("GIS", self.tr("Simple tag"), partial(run_tag, self))

        # # ########################################################################
        # # #################          Utils submenu         #########################
        self.add_menu_action("Data", self.tr("Import matrices"), partial(load_matrices, self))
        self.add_menu_action("Utils", self.tr("Display Matrices and datasets"), partial(display_aequilibrae_formats, self))

        # # ########################################################################
        # # #################          LOOSE STUFF         #########################

        self.add_menu_action("AequilibraE", self.tr("About"), partial(run_about, self))
        self.add_menu_action("AequilibraE", self.tr("Help"), self.run_help)

        self.build_menu()
        # ########################################################################
        # #################        PROJECT MANAGER       #########################

        self.showing = QCheckBox()
        self.showing.setText(self.tr("Show project info"))
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
        if main_menu == "AequilibraE":
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
            if menu == "AequilibraE":
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
        url = "http://aequilibrae.com/qgis"
        if sys.platform == "darwin":  # in case of OS X
            subprocess.Popen(["open", url])
        else:
            webbrowser.open_new_tab(url)

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
        self.matrices.clear()
        self.layers.clear()

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
        if self.project is None:
            return
        if layer_name.lower() not in self.layers:
            print("Layer was not found, which is weird")
            self.create_layer_by_name(layer_name)
        layer = self.layers[layer_name.lower()][0]
        QgsProject.instance().addMapLayer(layer)
        qgis.utils.iface.mapCanvas().refresh()

    def create_layer_by_name(self, layer_name: str):
        layer = self.create_loose_layer(layer_name)
        self.layers[layer_name.lower()] = [layer, layer.id()]

    def create_loose_layer(self, layer_name: str) -> QgsVectorLayer:
        if self.project is None:
            return
        uri = QgsDataSourceUri()
        uri.setDatabase(self.project.path_to_file)
        uri.setDataSource("", layer_name, "geometry")
        layer = QgsVectorLayer(uri.uri(), layer_name, "spatialite")
        return layer

    def run_load_database(self):
        dlg2 = LoadDatasetDialog(self.iface, single_use=False)
        dlg2.show()
        dlg2.exec_()

    def show_message_no_project(self):
        self.iface.messageBar().pushMessage("Error", self.tr("You need to load a project first"), level=3, duration=10)

    def message_project_already_open(self):
        self.iface.messageBar().pushMessage(self.tr("You need to close the project currently open first"), level=2, duration=10)

    def set_font(self, obj):
        f = obj.font()
        f.setPointSize(11)
        obj.setFont(f)

    def tr(self, text):
        return QtCore.QCoreApplication.translate("aequilibrae", text)
import glob
import logging
import os
import subprocess
import sys
import tempfile
import webbrowser
from functools import partial
from typing import Dict
from uuid import uuid4

import qgis

from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtWidgets import QVBoxLayout, QApplication
from qgis.PyQt.QtWidgets import QWidget, QDockWidget, QAction, QMenu, QTabWidget, QCheckBox, QToolBar, QToolButton
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsVectorFileWriter
from qgis.core import QgsProject, QgsExpressionContextUtils, QgsApplication
from qgis.PyQt.QtCore import QTranslator

from qaequilibrae.modules.processing_provider.provider import Provider
from qaequilibrae.modules.menu_actions import load_matrices, run_add_connectors, run_stacked_bandwidths, run_tag
from qaequilibrae.modules.menu_actions import run_add_zones, run_show_project_data
from qaequilibrae.modules.menu_actions import run_desire_lines, run_scenario_comparison, run_lcd, run_import_gtfs
from qaequilibrae.modules.menu_actions import (
    run_distribution_models,
    run_tsp,
    run_change_parameters,
    prepare_network,
)
from qaequilibrae.modules.menu_actions import (
    run_load_project,
    project_from_osm,
    run_create_transponet,
    show_log,
    create_example,
)
from qaequilibrae.modules.menu_actions import run_pt_explore
from qaequilibrae.modules.paths_procedures import run_shortest_path, run_dist_matrix, run_traffic_assig
from qaequilibrae.message import messages

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages"))
    from aequilibrae.project import Project
except:
    version = sys.version_info

    msg = messages()
    from qgis.PyQt.QtWidgets import QMessageBox

    if version < (3, 12) and sys.platform == "win32":
        QMessageBox.information(None, "Warning", msg.messsage_five)
    else:
        if (
            QMessageBox.question(None, msg.first_box_name, msg.first_message, QMessageBox.Ok | QMessageBox.Cancel)
            == QMessageBox.Ok
        ):
            from qaequilibrae.download_extra_packages_class import DownloadAll

            result = DownloadAll().install()
            if "ERROR" in "".join([str(x).upper() for x in result]):
                QMessageBox.information(None, "Information", msg.second_message)
            else:
                QMessageBox.information(None, "Information", msg.third_message)
        else:
            QMessageBox.information(None, "Information", msg.fourth_message)

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
        self.dock = QDockWidget("AequilibraE")
        self.manager = QWidget()
        self.provider = None

        # The self.toolbar will hold everything
        self.toolbar = QToolBar()
        self.set_font(self.toolbar)
        self.toolbar.setOrientation(2)

        if QtCore.QSettings().value("locale/overrideFlag", type=bool):
            loc = QtCore.QSettings().value("locale/userLocale")
        else:
            loc = QtCore.QLocale.system().name()
        loc = loc if len(loc) == 5 else loc[:2]

        locale_path = "{}/i18n/qaequilibrae_{}.qm".format(os.path.dirname(__file__), loc)

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QtCore.QCoreApplication.installTranslator(self.translator)

        self.menuActions = {
            self.tr("Project"): [],
            self.tr("Model Building"): [],
            self.tr("Data"): [],
            self.tr("Trip Distribution"): [],
            self.tr("Paths and assignment"): [],
            self.tr("Routing"): [],
            self.tr("Public Transport"): [],
            "GIS": [],
            "AequilibraE": [],
        }

        # # #######################   PROJECT SUB-MENU   ############################
        self.add_menu_action(self.tr("Project"), self.tr("Open Project"), partial(run_load_project, self))
        self.add_menu_action(self.tr("Project"), self.tr("Create example"), partial(create_example, self))
        self.add_menu_action(self.tr("Project"), self.tr("Parameters"), partial(run_change_parameters, self))
        self.add_menu_action(self.tr("Project"), self.tr("logfile"), partial(show_log, self))
        self.add_menu_action(self.tr("Project"), self.tr("Close project"), self.run_close_project)

        # # # ########################################################################
        # # # ################# MODEL BUILDING SUB-MENU  #######################
        self.add_menu_action(
            self.tr("Model Building"), self.tr("Create project from OSM"), partial(project_from_osm, self)
        )
        self.add_menu_action(
            self.tr("Model Building"), self.tr("Create Project from layers"), partial(run_create_transponet, self)
        )
        self.add_menu_action(self.tr("Model Building"), self.tr("Network Preparation"), partial(prepare_network, self))
        self.add_menu_action(
            self.tr("Model Building"), self.tr("Add centroid connectors"), partial(run_add_connectors, self)
        )
        self.add_menu_action(self.tr("Model Building"), self.tr("Add zoning data"), partial(run_add_zones, self))

        # # # ########################################################################
        # # # ####################  DATA UTILITIES SUB-MENU  #########################
        self.add_menu_action(self.tr("Data"), self.tr("Visualize data"), partial(run_show_project_data, self))
        self.add_menu_action(self.tr("Data"), self.tr("Import matrices"), partial(load_matrices, self))

        # # # # ########################################################################
        # # # # ##################  TRIP DISTRIBUTION SUB-MENU  ########################
        self.add_menu_action(
            self.tr("Trip Distribution"), self.tr("Trip Distribution"), partial(run_distribution_models, self)
        )

        # # # ########################################################################
        # # # ###################  PATH COMPUTATION SUB-MENU   #######################
        self.add_menu_action(
            self.tr("Paths and assignment"), self.tr("Shortest path"), partial(run_shortest_path, self)
        )
        self.add_menu_action(
            self.tr("Paths and assignment"), self.tr("Impedance matrix"), partial(run_dist_matrix, self)
        )
        self.add_menu_action(
            self.tr("Paths and assignment"), self.tr("Traffic Assignment"), partial(run_traffic_assig, self)
        )

        # # # ########################################################################
        # # # #######################   ROUTING SUB-MENU   ###########################
        self.add_menu_action(self.tr("Routing"), self.tr("Travelling Salesman Problem"), partial(run_tsp, self))

        # # # ########################################################################
        # # # #######################   TRANSIT SUB-MENU   ###########################
        self.add_menu_action(self.tr("Public Transport"), self.tr("Import GTFS"), partial(run_import_gtfs, self))
        self.add_menu_action(self.tr("Public Transport"), self.tr("Explore Transit"), partial(run_pt_explore, self))

        # # ########################################################################
        # # #################        GIS TOOLS SUB-MENU    #########################
        self.add_menu_action("GIS", self.tr("Desire Lines"), partial(run_desire_lines, self))
        self.add_menu_action("GIS", self.tr("Stacked Bandwidth"), partial(run_stacked_bandwidths, self))
        self.add_menu_action("GIS", self.tr("Scenario Comparison"), partial(run_scenario_comparison, self))
        self.add_menu_action("GIS", self.tr("Lowest common denominator"), partial(run_lcd, self))
        self.add_menu_action("GIS", self.tr("Simple tag"), partial(run_tag, self))

        # # ########################################################################
        # # #################          LOOSE STUFF         #########################
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

        # # # ########################################################################
        # ##################        SAVING PROJECT CONFIGS       #####################
        QgsProject.instance().readProject.connect(self.reload_project)

        temp_saving = self.iface.mainWindow().findChild(QAction, "mActionSaveProject")
        if temp_saving:
            temp_saving.triggered.connect(self.save_in_project)

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

    # def trlt(self, message):
    #     # In the near future, we will use this function to automatically translate the AequilibraE menu
    #     # To any language we can get people to translate it to
    #     # return QCoreApplication.translate('AequilibraE', message)
    #     return message

    def initProcessing(self):
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        if self.provider in QgsApplication.processingRegistry().providers():
            QgsApplication.processingRegistry().removeProvider(self.provider)

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
        self.remove_aequilibrae_layers()
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
        if not "transit_" in layer_name:
            uri.setDatabase(self.project.path_to_file)
            lname = layer_name
        else:
            uri.setDatabase(os.path.join(self.project.project_base_path, "public_transport.sqlite"))
            lname = layer_name[8:]
        uri.setDataSource("", lname, "geometry")
        layer = QgsVectorLayer(uri.uri(), layer_name, "spatialite")
        return layer

    def show_message_no_project(self):
        self.iface.messageBar().pushMessage("Error", self.tr("You need to load a project first"), level=3, duration=10)

    def message_project_already_open(self):
        self.iface.messageBar().pushMessage(
            "Error", self.tr("You need to close the project currently open first"), level=2, duration=10
        )

    def set_font(self, obj):
        f = obj.font()
        f.setPointSize(11)
        obj.setFont(f)

    def tr(self, text):
        return QCoreApplication.translate("AequilibraEMenu", text)

    def reload_project(self):
        """Opens AequilibraE project when opening a QGIS project containing an AequilibraE model."""
        from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

        # Checks if project contains an AequilibraE model
        path = QgsProject.instance().customVariables()
        if "aequilibrae_path" not in path:
            return

        # Opens project
        _run_load_project_from_path(self, path["aequilibrae_path"])

        # Checks if the layers in the project have the same database path as the aequilibrae project layers.
        # if so, we replace the path in self.layers
        prj_layer_sources = [lyr.source() for lyr in QgsProject.instance().mapLayers().values()]
        prj_layers = [lyr for lyr in QgsProject.instance().mapLayers().values()]

        geo_source = [v[0].source().replace("\\\\", "/") for v in self.layers.values()]
        geo_names = [v[0].name() for v in self.layers.values()]

        for idx, lyr in enumerate(geo_source):
            if lyr in prj_layer_sources:
                lidx = prj_layer_sources.index(lyr)
                self.layers[geo_names[idx]] = [prj_layers[lidx], prj_layers[lidx].id()]

    def remove_aequilibrae_layers(self):
        """Removes layers connected to current aequilibrae project from active layers if the
        active project is closed.
        """
        aequilibrae_databases = ["project_database", "public_transport", "results_database"]

        for layer in QgsProject.instance().mapLayers().values():
            dbpath = layer.source().split("dbname='")[-1].split("' table")[0]
            dbpath = dbpath.split("|")[0].split(".sqlite")[0]
            var = os.path.split(dbpath)
            if var[0] == self.project.project_base_path and var[1] in aequilibrae_databases:
                QgsProject.instance().removeMapLayer(layer)

        qgis.utils.iface.mapCanvas().refresh()

    def save_in_project(self):
        """Saves temporary layers to the project using QGIS saving buttons."""
        if not self.project:
            return

        path = QgsProject.instance().customVariables()

        if "aequilibrae_path" not in path:
            QgsExpressionContextUtils.setProjectVariable(
                QgsProject.instance(), "aequilibrae_path", self.project.project_base_path
            )

        output_file_path = os.path.join(self.project.project_base_path, "qgis_layers.sqlite")

        file_exists = True if os.path.isfile(output_file_path) else False

        for layer in QgsProject.instance().mapLayers().values():
            if layer.isTemporary():
                layer_name = layer.name() + f"_{uuid4().hex}"
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "SQLite"
                options.layerName = layer_name
                if file_exists:
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

                transform_context = QgsProject.instance().transformContext()

                error = QgsVectorFileWriter.writeAsVectorFormatV3(layer, output_file_path, transform_context, options)

                if error[0] == QgsVectorFileWriter.NoError:
                    layer.setDataSource(output_file_path + f"|layername={layer_name}", layer.name(), "ogr")

                file_exists = True

        QgsProject.instance().write()

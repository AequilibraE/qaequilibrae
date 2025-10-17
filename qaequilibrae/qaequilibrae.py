import glob
import subprocess
import sys
import tempfile
import webbrowser
from functools import partial
from os import unlink
from os.path import dirname, exists, join, isfile
from pathlib import Path
from uuid import uuid4

import qgis
from qgis.PyQt.QtCore import Qt, QTranslator, QSettings, QLocale, QCoreApplication, QSize
from qgis.PyQt.QtWidgets import QVBoxLayout, QApplication, QToolBar, QToolButton
from qgis.PyQt.QtWidgets import QWidget, QDockWidget, QAction, QMenu, QTabWidget
from qgis.PyQt.QtWidgets import QComboBox, QLabel, QTableWidgetItem, QTableWidget
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsVectorFileWriter
from qgis.core import QgsProject, QgsExpressionContextUtils, QgsApplication, QgsMessageLog, Qgis

from qaequilibrae import set_aequilibrae_menu_instance
from qaequilibrae.message import messages
from qaequilibrae.modules.menu_actions import run_load_project, run_module, run_show_project_data
from qaequilibrae.modules.menu_actions import run_desire_lines, run_scenario_comparison, run_import_gtfs
from qaequilibrae.modules.menu_actions import run_distribution_models, run_stacked_bandwidths, run_pt_explore
from qaequilibrae.modules.menu_actions import run_shortest_path, run_dist_matrix, run_traffic_assig, create_scenarios
from qaequilibrae.modules.menu_actions import run_route_choice, run_pt_skim, last_folder, load_skim_viewer
from qaequilibrae.modules.processing_provider.provider import Provider

sys.path.insert(0, join(dirname(__file__), "packages"))

if Path(join(dirname(__file__), "packages", "requirements.txt")).exists():
    pass
else:
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
            if result > 0:
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
        set_aequilibrae_menu_instance(self)
        # Closes AequilibraE projects eventually opened in memory
        self.logger = self.get_logger()
        self.geo_layers_list = ["links", "nodes", "zones"]
        self.available_scenarios = []
        self.iface = iface
        self.path = last_folder()
        self.project = None  # type: Project
        self.matrices = {}
        self.layers = {}  # type: Dict[QgsVectorLayer]
        self.dock = QDockWidget("AequilibraE")
        self.manager = QWidget()
        self.provider = None
        self.dialog_depth: int = 0

        # The self.toolbar will hold everything
        self.toolbar = QToolBar()
        self.set_font(self.toolbar)
        self.toolbar.setOrientation(2)

        if QSettings().value("locale/overrideFlag", type=bool):
            loc = QSettings().value("locale/userLocale")
        else:
            loc = QLocale.system().name()
        loc = loc if len(loc) == 5 else loc[:2]

        locale_path = "{}/i18n/qaequilibrae_{}.qm".format(dirname(__file__), loc)

        if exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.menuActions = {
            self.tr("Project"): [],
            self.tr("Trip distribution"): [],
            self.tr("Path computation"): [],
            self.tr("Traffic assignment"): [],
            self.tr("Route choice"): [],
            self.tr("Transit"): [],
            self.tr("Mapping"): [],
            "AequilibraE": [],
        }

        # # # ########################################################################
        # # # #######################  PROJECT SUB-MENU  #############################
        mmenu = self.tr("Project")
        self.add_menu_action(mmenu, self.tr("Open project"), partial(run_load_project, self))
        self.add_menu_action(mmenu, self.tr("Run procedures"), partial(run_module, self))
        self.add_menu_action(mmenu, self.tr("Scenarios"), partial(create_scenarios, self))
        self.add_menu_action(mmenu, self.tr("Close project"), self.run_close_project)

        # # # ########################################################################
        # # # ##################  TRIP DISTRIBUTION SUB-MENU  ########################
        mmenu = self.tr("Trip distribution")
        self.add_menu_action(mmenu, self.tr("Trip distribution"), partial(run_distribution_models, self))

        # # # ########################################################################
        # # # ###################  PATH COMPUTATION SUB-MENU  ########################
        mmenu = self.tr("Path computation")
        self.add_menu_action(mmenu, self.tr("Shortest path"), partial(run_shortest_path, self))
        self.add_menu_action(mmenu, self.tr("Impedance matrix"), partial(run_dist_matrix, self))
        self.add_menu_action(mmenu, self.tr("Skim viewer"), partial(load_skim_viewer, self))

        # # # ########################################################################
        # # # ###################  TRAFFIC ASSIGNMENT SUB-MENU  ######################
        mmenu = self.tr("Traffic assignment")
        self.add_menu_action(mmenu, self.tr("Traffic assignment"), partial(run_traffic_assig, self))

        # # # ########################################################################
        # # # ###################  ROUTE CHOICE SUB-MENU  ############################
        mmenu = self.tr("Route choice")
        self.add_menu_action(mmenu, self.tr("Route choice"), partial(run_route_choice, self))

        # # # ########################################################################
        # # # ###################  TRANSIT SUB-MENU  #################################
        mmenu = self.tr("Transit")
        self.add_menu_action(mmenu, self.tr("Import GTFS"), partial(run_import_gtfs, self))
        self.add_menu_action(mmenu, self.tr("Skimming and assignment"), partial(run_pt_skim, self))
        self.add_menu_action(mmenu, self.tr("Explore transit"), partial(run_pt_explore, self))

        # # # ########################################################################
        # # # ###################  GIS TOOLS SUB-MENU  ###############################
        mmenu = self.tr("Mapping")
        self.add_menu_action(mmenu, self.tr("Visualize data"), partial(run_show_project_data, self))
        self.add_menu_action(mmenu, self.tr("Desire lines"), partial(run_desire_lines, self))
        self.add_menu_action(mmenu, self.tr("Stacked bandwidth"), partial(run_stacked_bandwidths, self))
        self.add_menu_action(mmenu, self.tr("Scenario comparison"), partial(run_scenario_comparison, self))

        # # # ########################################################################
        # # # ###################  LOOSE STUFF  ######################################
        self.add_menu_action("AequilibraE", self.tr("Help"), self.run_help)

        self.build_menu()
        # # # ########################################################################
        # # # ###################  PROJECT MANAGER  ##################################

        lbl = QLabel("Model scenario")
        lbl.setAlignment(Qt.AlignCenter)
        self.toolbar.addWidget(lbl)
        self.cob_scenarios = QComboBox()
        self.toolbar.addWidget(self.cob_scenarios)

        self.cob_scenarios.currentIndexChanged.connect(self.configure_scenario)

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
        QgsProject.instance().layerRemoved.connect(self.layerRemoved)

        # # # ########################################################################
        # ##################        SAVING PROJECT CONFIGS       #####################
        QgsProject.instance().readProject.connect(self.reload_project)

        for action in ["mActionSaveProject", "mActionSaveProjectAs"]:
            temp_saving = self.iface.mainWindow().findChild(QAction, action)
            if temp_saving:
                temp_saving.triggered.connect(self.save_in_project)

    def get_logger(self):
        from aequilibrae.context import get_logger

        return get_logger()

    def configure_scenario(self):
        if self.cob_scenarios.currentIndex() < 0:
            return

        if self.available_scenarios:
            name = self.available_scenarios[self.cob_scenarios.currentIndex()]
            self.project.use_scenario(name)
            self.message_log(self.tr("Changed active scenario: {}").format(name))

            # Change layers
            tab_count = self.projectManager.count()
            for i in range(tab_count):
                self.projectManager.removeTab(i)
            self.update_project_layers()

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
        url = "http://www.aequilibrae.com/latest/qgis/index.html"
        if sys.platform == "darwin":  # in case of OS X
            subprocess.Popen(["open", url])
        else:
            webbrowser.open_new_tab(url)

    def initProcessing(self):
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        if self.provider in QgsApplication.processingRegistry().providers():
            QgsApplication.processingRegistry().removeProvider(self.provider)

    def removes_temporary_files(self):
        # Removes all the temporary files from previous uses
        p = tempfile.gettempdir() + "/aequilibrae_*"
        for f in glob.glob(p):
            try:
                unlink(f)
            except Exception as e:
                self.logger.error(e.args)
                pass

    def run_close_project(self):
        if not self.project:
            return
        self.remove_aequilibrae_layers()
        self.project.use_scenario("root")
        pth = str(self.project.project_base_path)
        self.project.close()
        self.cob_scenarios.clear()
        self.projectManager.clear()
        self.project = None
        self.available_scenarios = []
        self.matrices.clear()
        self.layers.clear()
        self.message_log(self.tr("Closed project on: {}").format(pth))

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
        if not self.project:
            return
        uri = QgsDataSourceUri()
        if "transit_" not in layer_name:
            uri.setDatabase(str(self.project._project_database_path))
            lname = layer_name
        else:
            uri.setDatabase(str(self.project._transit_database_path))
            lname = layer_name[8:]
        uri.setDataSource("", lname, "geometry")
        suffix = self.available_scenarios[self.cob_scenarios.currentIndex()]
        name = layer_name if suffix == "root" else f"{layer_name}_{suffix}"
        layer = QgsVectorLayer(uri.uri(), name, "spatialite")
        return layer

    def show_message_no_project(self):
        self.iface_error_message(text=self.tr("You need to load a project"))

    def message_project_already_open(self):
        self.iface_error_message(text=self.tr("You need to close the currently open project"))

    def message_no_gtfs_feed(self):
        self.iface_error_message(text=self.tr("You need to import a GTFS feed"))

    def set_font(self, obj):
        f = obj.font()
        f.setPointSize(11)
        obj.setFont(f)

    def tr(self, text):
        return QCoreApplication.translate("AequilibraEMenu", text)

    def reload_project(self):
        """Opens AequilibraE project when opening a QGIS project containing an AequilibraE model."""
        from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path

        # Check if QGIS project contains an AequilibraE model
        path = QgsProject.instance().customVariables()
        if "aequilibrae_path" in path:
            # Open AequilibraE project
            _run_load_project_from_path(self, path["aequilibrae_path"])

            # Go back to last scenario
            if "aeq_scenario" in path:
                self.cob_scenarios.setCurrentText(path["aeq_scenario"])
                self.project.use_scenario(path["aeq_scenario"])
        else:
            return

        # Check if the layers in the project have the same database path as the aequilibrae project layers.
        # if so, we replace the path in self.layers
        for lyr in QgsProject.instance().mapLayers().values():
            if "sqlite" not in lyr.source():
                continue
            self.layers[str(lyr.name()).lower()] = [lyr, lyr.id()]

    def remove_aequilibrae_layers(self):
        """Removes layers connected to current aequilibrae project from active layers if the
        active project is closed.
        """
        aequilibrae_databases = ["project_database", "public_transport", "results_database"]

        for layer in QgsProject.instance().mapLayers().values():
            dbpath = layer.source().split("dbname='")[-1].split("' table")[0]
            dbpath = Path(dbpath).stem
            if dbpath in aequilibrae_databases:
                QgsProject.instance().removeMapLayer(layer)

        qgis.utils.iface.mapCanvas().refresh()

    def _project_base_path(self):
        if "/scenarios/" in str(self.project.project_base_path):
            return self.project.project_base_path.parent.parent
        return self.project.project_base_path

    def _project_layers_database(self):
        return str(self._project_base_path() / "qgis_layers.sqlite")

    def save_in_project(self):
        """Saves temporary layers to the project using QGIS saving buttons."""
        if not self.project:
            return

        variables = QgsProject.instance().customVariables()

        if "aequilibrae_path" not in variables:
            QgsExpressionContextUtils.setProjectVariable(
                QgsProject.instance(), "aequilibrae_path", str(self._project_base_path())
            )
        # Create project variable 'aeq_scenario' to store scenario info
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), "aeq_scenario", self.cob_scenarios.currentText()
        )

        file_exists = True if isfile(self._project_layers_database()) else False

        for layer in QgsProject.instance().mapLayers().values():
            if layer.isTemporary():
                layer_name = layer.name() + f"_{uuid4().hex}"
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "SQLite"
                options.layerName = layer_name
                if file_exists:
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

                transform_context = QgsProject.instance().transformContext()

                error = QgsVectorFileWriter.writeAsVectorFormatV3(
                    layer, self._project_layers_database(), transform_context, options
                )

                if error[0] == QgsVectorFileWriter.NoError:
                    layer.setDataSource(
                        self._project_layers_database() + f"|layername={layer_name}", layer.name(), "ogr"
                    )

                file_exists = True

        QgsProject.instance().write()

    def update_project_layers(self):
        with self.project.db_connection_spatial as conn:
            layers = [x[0] for x in conn.execute("select f_table_name from geometry_columns;").fetchall()]

            # Add transit_tables to layers
            if exists(self.project._transit_database_path):
                layers += ["transit_links", "transit_routes", "transit_stops", "transit_pattern_mapping"]

            descrlayout = QVBoxLayout()
            self.geo_layers_table = QTableWidget()
            self.geo_layers_table.doubleClicked.connect(self.load_geo_layer)

            self.geo_layers_table.setRowCount(len(layers))
            self.geo_layers_table.setColumnCount(1)
            self.geo_layers_table.horizontalHeader().hide()
            for i, f in enumerate(layers):
                item1 = QTableWidgetItem(f)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.geo_layers_table.setItem(i, 0, item1)

            descrlayout.addWidget(self.geo_layers_table)

            descr = QWidget()
            descr.setLayout(descrlayout)
            self.tabContents = [(descr, "Geo layers")]
            for i in range(self.projectManager.count()):
                self.projectManager.removeTab(i)
            self.projectManager.addTab(descr, "Geo layers")
            conn.execute("PRAGMA temp_store = 0;")

            # Creates all layers and puts them in memory
            self.layers.clear()
            for lyr in layers:
                self.create_layer_by_name(lyr)

    def message_log(self, message, level: Qgis.MessageLevel = Qgis.MessageLevel.Info, notify_user: bool = False):
        """
        Standardizes QAequilibraE message log display in the tab 'Messages'.

        Uses 'Info' level and does not notify user, by default, although these are editable.
        """
        QgsMessageLog.logMessage(message, self.tr("Messages"), level, notify_user)

    def iface_error_message(self, text: str = None, title: str = "Error"):
        """Standardizes QAequilibraE error messages display"""
        self.iface.messageBar().pushMessage(title, text, Qgis.MessageLevel.Critical, -1)

    def iface_info_message(self, text: str = None, title: str = "Info"):
        """Standardizes QAequilibraE info messages display"""
        self.iface.messageBar().pushMessage(title, text, Qgis.MessageLevel.Info, -1)

    def iface_warning_message(self, text: str = None, title: str = "Warning"):
        """Standardizes QAequilibraE warning messages display"""
        self.iface.messageBar().pushMessage(title, text, Qgis.MessageLevel.Warning, -1)

    def iface_success_message(self, text: str = None, title: str = "Success"):
        """Standardizes QAequilibraE warning messages display"""
        self.iface.messageBar().pushMessage(title, text, Qgis.MessageLevel.Success, -1)

    def allow_change_scenario(self):
        """
        Enables scenario changes after deactivation.

        This function is used with the QDialog finished signal, which is emitted when the dialog's
        result code has been set, either by the user or by calling done(), accept(), or reject().

        See: https://doc.qt.io/qt-6/qdialog.html#finished
        """
        self.dialog_depth -= 1
        if self.dialog_depth <= 0:
            self.cob_scenarios.setEnabled(True)
            self.dialog_depth = 0

    def block_change_scenario(self):
        """
        Disables scenario changes when QDialogs are open.

        This function is used when initializating classes with dialogs.
        """
        self.cob_scenarios.setEnabled(False)
        self.dialog_depth += 1

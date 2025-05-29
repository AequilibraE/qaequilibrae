from os.path import exists, join
from pathlib import Path
from tempfile import gettempdir

import qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem, QTableWidget
from qgis.PyQt.QtWidgets import QWidget, QFileDialog, QVBoxLayout


# Split loading between Qt action and processing, for easier unit testing
def run_load_project(qgis_project):
    from qaequilibrae.modules.common_tools.get_output_file_name import GetOutputFolderName

    proj_path = GetOutputFolderName(str(Path(qgis_project.path).parent), "AequilibraE Project folder")

    return _run_load_project_from_path(qgis_project, proj_path)


def _get_project_path():
    from qaequilibrae.modules.common_tools.auxiliary_functions import standard_path

    return QFileDialog.getExistingDirectory(QWidget(), "AequilibraE Project folder", standard_path())


def _run_load_project_from_path(qgis_project, proj_path):
    from aequilibrae.project import Project

    if proj_path is None or proj_path == "":
        return

    # Cleans the project descriptor
    tab_count = 1
    for i in range(tab_count):
        qgis_project.projectManager.removeTab(i)
    if proj_path is not None and len(proj_path) > 0:
        qgis_project.contents = []
        qgis_project.showing.setVisible(True)
        qgis_project.project = Project()

        try:
            qgis_project.project.open(proj_path)
        except FileNotFoundError as e:
            if e.args[0] == "Model does not exist. Check your path and try again":
                qgis.utils.iface.messageBar().pushMessage("FOLDER DOES NOT CONTAIN AN AEQUILIBRAE MODEL", level=1)
                return
            else:
                raise e

    pth = join(gettempdir(), "aequilibrae_last_folder.txt")
    with open(pth, "w") as file:
        file.write(proj_path)

    update_project_layers(qgis_project)


def update_project_layers(qgis_project):

    with qgis_project.project.db_connection as conn:
        layers = [x[0] for x in conn.execute("select f_table_name from geometry_columns;").fetchall()]

        # Add transit_tables to layers
        pt_database = join(qgis_project.project.project_base_path, "public_transport.sqlite")
        if exists(pt_database):
            layers += ["transit_links", "transit_routes", "transit_stops", "transit_pattern_mapping"]

        descrlayout = QVBoxLayout()
        qgis_project.geo_layers_table = QTableWidget()
        qgis_project.geo_layers_table.doubleClicked.connect(qgis_project.load_geo_layer)

        qgis_project.geo_layers_table.setRowCount(len(layers))
        qgis_project.geo_layers_table.setColumnCount(1)
        qgis_project.geo_layers_table.horizontalHeader().hide()
        for i, f in enumerate(layers):
            item1 = QTableWidgetItem(f)
            item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            qgis_project.geo_layers_table.setItem(i, 0, item1)

        descrlayout.addWidget(qgis_project.geo_layers_table)

        descr = QWidget()
        descr.setLayout(descrlayout)
        qgis_project.tabContents = [(descr, "Geo layers")]
        qgis_project.projectManager.addTab(descr, "Geo layers")
        conn.execute("PRAGMA temp_store = 0;")

        # Creates all layers and puts them in memory
        qgis_project.layers.clear()
        for lyr in layers:
            qgis_project.create_layer_by_name(lyr)

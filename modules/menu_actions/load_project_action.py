from aequilibrae.project import Project

import qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem, QTableWidget
from qgis.PyQt.QtWidgets import QWidget, QFileDialog, QVBoxLayout
from ..common_tools.auxiliary_functions import standard_path


# Split loading between Qt action and processing, for easier unit testing
def run_load_project(qgis_project):
    proj_path = _get_project_path()
    return _run_load_project_from_path(qgis_project, proj_path)


def _get_project_path():
    return QFileDialog.getExistingDirectory(QWidget(), "AequilibraE Project folder", standard_path())


def _run_load_project_from_path(qgis_project, proj_path):
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

    curr = qgis_project.project.conn.cursor()
    curr.execute("select f_table_name from geometry_columns;")
    layers = [x[0] for x in curr.fetchall()]

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
    qgis_project.project.conn.execute("PRAGMA temp_store = 0;")

    # Creates all layers and puts them in memory
    qgis_project.layers.clear()
    for lyr in layers:
        qgis_project.create_layer_by_name(lyr)

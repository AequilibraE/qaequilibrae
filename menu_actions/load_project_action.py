from aequilibrae import Project
from qgis.PyQt.QtWidgets import QWidget, QFileDialog
from ..common_tools.auxiliary_functions import standard_path


def run_load_project(qgis_project):
    proj_path = QFileDialog.getExistingDirectory(QWidget(), "AequilibraE Project folder", standard_path())

    # Cleans the project descriptor
    tab_count = 1
    for i in range(tab_count):
        qgis_project.projectManager.removeTab(i)
    if proj_path is not None and len(proj_path) > 0:
        qgis_project.contents = []
        qgis_project.showing.setVisible(True)
        qgis_project.project = Project()

        try:
            qgis_project.project.load(proj_path)
        except FileNotFoundError as e:
            if e.args[0] == 'Model does not exist. Check your path and try again':
                qgis.utils.iface.messageBar().pushMessage("FOLDER DOES NOT CONTAIN AN AEQUILIBRAE MODEL", level=1)
                return
            else:
                raise e

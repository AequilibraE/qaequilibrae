from pathlib import Path

import qgis

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


def close_project_action():
    """
    We move the functions ``run_close_project`` and ``remove_aequilibrae_layers``
    from AequilibraEMenu to the processing provider.
    """
    proj = get_aequilibrae_menu_instance()

    file_path = str(proj.project.project_base_path)
    remove_aequilibrae_layers()
    proj.project.close()
    proj.projectManager.clear()
    proj.project = None
    proj.matrices.clear()
    proj.layers.clear()

    qgis.utils.iface.messageBar().pushInfo("Project closed", file_path)


def remove_aequilibrae_layers():
    """
    Removes layers connected to current aequilibrae project from active layers if the
    active project is closed.
    """
    aequilibrae_databases = ["project_database", "public_transport", "results_database"]

    for layer in qgis.core.QgsProject.instance().mapLayers().values():
        dbpath = layer.source().split("dbname='")[-1].split("' table")[0]
        dbpath = Path(dbpath).stem
        if dbpath in aequilibrae_databases:
            qgis.core.QgsProject.instance().removeMapLayer(layer)

    qgis.utils.iface.mapCanvas().refresh()


class CloseProject(QAequilibraEProcessingAlgorithm):

    def __init__(self):
        super().__init__(
            close_project_action,
            "close_project",
            self.tr("Close project"),
            self.tr("Project"),
            "project_procedures",
            self.tr("Close AequilibraE project into QGIS."),
            ["close", "project", "close project"],
        )

    def createInstance(self):
        return CloseProject()

    def tr(self, message):
        return trlt("CloseProject", message)

import qgis

from qaequilibrae import get_aequilibrae_menu_instance
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.processing_provider.base_algorithm import QAequilibraEProcessingAlgorithm


def close_project_action():
    proj = get_aequilibrae_menu_instance()
    proj.close()

    qgis.utils.iface.messageBar().pushInfo("Project closed", proj.project_base_path)


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

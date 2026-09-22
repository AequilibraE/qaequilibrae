"""Base helpers for Processing algorithms that work with project folders."""

from qgis.core import Qgis, QgsProcessingAlgorithm, QgsProcessingParameterFile

from qaequilibrae.i18n.translate import trlt


class ProjectAlgorithm(QgsProcessingAlgorithm):
    """Common project-folder parameter and toolbox metadata."""

    PROJECT_FOLDER = "PROJECT_FOLDER"
    group_name = "AequilibraE project"
    group_id = "aequilibrae_project"

    def add_project_folder_parameter(self):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECT_FOLDER,
                self.tr("AequilibraE project folder"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )

    def project_folder(self, parameters, context):
        return self.parameterAsFile(parameters, self.PROJECT_FOLDER, context)

    def group(self):
        return self.tr(self.group_name)

    def groupId(self):
        return self.group_id

    def tr(self, message):
        return trlt(type(self).__name__, message)


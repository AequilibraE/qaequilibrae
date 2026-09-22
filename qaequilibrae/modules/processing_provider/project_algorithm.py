"""Base helpers for Processing algorithms that work with project folders."""

from qgis.core import Qgis, QgsProcessingAlgorithm, QgsProcessingParameterFile

from qaequilibrae.i18n.translate import trlt


class ProjectAlgorithm(QgsProcessingAlgorithm):
    """Common project-folder parameter and toolbox metadata."""

    PROJECT_FOLDER = "PROJECT_FOLDER"
    group_name = "AequilibraE project"
    group_id = "aequilibrae_project"

    def add_project_folder_parameter(self, name: str | None = None):
        """Add a project-folder parameter, optionally retaining a legacy key."""
        self.addParameter(
            QgsProcessingParameterFile(
                name or self.PROJECT_FOLDER,
                self.tr("AequilibraE project folder"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )

    def project_folder(self, parameters, context, name: str | None = None):
        """Resolve the configured project-folder parameter."""
        return self.parameterAsFile(parameters, name or self.PROJECT_FOLDER, context)

    def group(self):
        return self.tr(self.group_name)

    def groupId(self):
        return self.group_id

    def tr(self, message):
        return trlt(type(self).__name__, message)

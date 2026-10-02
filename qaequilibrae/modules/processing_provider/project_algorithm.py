"""Shared base classes for AequilibraE Processing algorithms."""

from qgis.core import Qgis, QgsProcessingAlgorithm, QgsProcessingParameterFile

from qaequilibrae.i18n.translate import trlt


class ProcessingAlgorithm(QgsProcessingAlgorithm):
    """Shared metadata, translation, and instance creation for provider algorithms."""

    algorithm_name = ""
    display_name = ""
    group_name = "AequilibraE"
    group_id = "aequilibrae"
    translate_algorithm_name = False
    translation_context: str | None = None

    def name(self) -> str:
        if self.translate_algorithm_name:
            return self.tr(self.algorithm_name)
        return self.algorithm_name

    def displayName(self) -> str:
        return self.tr(self.display_name)

    def group(self) -> str:
        return self.tr(self.group_name)

    def groupId(self) -> str:
        return self.group_id

    def createInstance(self) -> QgsProcessingAlgorithm:
        return type(self)()

    def tr(self, message: str) -> str:
        context = self.translation_context or type(self).__name__
        return trlt(context, message)


class ProjectAlgorithm(ProcessingAlgorithm):
    """Add project-folder parameters to algorithms that use a project."""

    PROJECT_FOLDER = "PROJECT_FOLDER"
    group_name = "AequilibraE project"
    group_id = "aequilibrae_project"

    def add_project_folder_parameter(self, name: str | None = None) -> None:
        """Add a project-folder parameter, optionally retaining a legacy key."""
        self.addParameter(
            QgsProcessingParameterFile(
                name or self.PROJECT_FOLDER,
                self.tr("AequilibraE project folder"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )

    def project_folder(self, parameters, context, name: str | None = None) -> str:
        """Resolve the configured project-folder parameter."""
        return self.parameterAsFile(parameters, name or self.PROJECT_FOLDER, context)

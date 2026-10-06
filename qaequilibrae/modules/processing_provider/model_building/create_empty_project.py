import importlib.util as iutil
from os import listdir, rmdir
from os.path import isdir, join

from qgis.core import Qgis, QgsProcessingException, QgsProcessingParameterFile, QgsProcessingParameterString

from qaequilibrae.modules.processing_provider.project_algorithm import ProcessingAlgorithm


class CreateEmptyProject(ProcessingAlgorithm):
    algorithm_name = "create_empty_project"
    display_name = "Create empty project"
    group_name = "Model building"
    group_id = "model_building"

    PARENT_FOLDER = "PARENT_FOLDER"
    MODEL_NAME = "MODEL_NAME"

    # The model name is also the folder name.
    INVALID_NAME_CHARACTERS = '\\/:*?"<>|'

    # These names would point to the parent folder or its parent.
    RESERVED_NAMES = (".", "..")

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PARENT_FOLDER, self.tr("Parent folder"), behavior=Qgis.ProcessingFileParameterBehavior.Folder
            )
        )

        self.addParameter(
            QgsProcessingParameterString(self.MODEL_NAME, self.tr("Model name"), defaultValue="new model")
        )

    def flags(self):
        # The plugin panel's widgets require the main thread.
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def processAlgorithm(self, parameters, context, feedback):
        parent_folder = self.parameterAsFile(parameters, self.PARENT_FOLDER, context)
        model_name = self.parameterAsString(parameters, self.MODEL_NAME, context).strip()

        if not isdir(parent_folder):
            raise QgsProcessingException(self.tr("Parent folder does not exist: ") + parent_folder)

        if not model_name:
            raise QgsProcessingException(self.tr("The model name cannot be empty"))

        if any(char in model_name for char in self.INVALID_NAME_CHARACTERS):
            raise QgsProcessingException(
                self.tr("The model name cannot contain any of these characters: ") + self.INVALID_NAME_CHARACTERS
            )

        # Check before the empty-folder cleanup below.
        if model_name in self.RESERVED_NAMES:
            raise QgsProcessingException(self.tr("The model name cannot be '.' or '..'"))

        project_folder = join(parent_folder, model_name)

        if iutil.find_spec("aequilibrae") is None:
            raise QgsProcessingException(self.tr("AequilibraE module not found"))

        from aequilibrae.project import Project

        # AequilibraE needs a folder that does not exist yet.
        if isdir(project_folder):
            if listdir(project_folder):
                raise QgsProcessingException(self.tr("Folder already exists and is not empty: ") + project_folder)
            try:
                rmdir(project_folder)
            except OSError as e:
                raise QgsProcessingException(
                    self.tr("Could not remove empty folder: ") + project_folder + f" ({e})"
                ) from e
        feedback.pushInfo(self.tr("Creating project"))

        project = Project()
        try:
            project.new(project_folder)
        except Exception as e:
            raise QgsProcessingException(self.tr("Could not create project: ") + str(e)) from e

        modes = list(project.network.modes.all_modes().keys())
        link_types = list(project.network.link_types.all_types().keys())

        feedback.pushInfo(self.tr("Project created in ") + project_folder)
        feedback.pushInfo(self.tr("Default modes: ") + ", ".join(sorted(modes)))
        feedback.pushInfo(self.tr("Default link types: ") + ", ".join(sorted(link_types)))

        self.show_in_panel(project, project_folder, feedback)

        return {"Output": project_folder}

    def show_in_panel(self, project, project_folder, feedback):
        """Show the new project in the plugin panel when available."""
        from qaequilibrae import get_aequilibrae_menu_instance
        from qaequilibrae.modules.menu_actions.load_project_action import show_project_in_panel

        qgis_project = get_aequilibrae_menu_instance()

        if qgis_project is None:
            project.close()
            return

        if qgis_project.project is not None:
            feedback.pushWarning(self.tr("Close the open project to see the new one in the panel"))
            project.close()
            return

        qgis_project.project = project
        show_project_in_panel(qgis_project, project_folder)

    def shortHelpString(self):
        return self.tr(
            "Creates an empty AequilibraE project with default modes and link types. "
            "The project folder uses the model name and must be new or empty."
        )

    def tags(self):
        return ["create", "new", "empty", "project", "model"]

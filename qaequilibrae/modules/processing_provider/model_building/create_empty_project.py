import importlib.util as iutil
from os import listdir, rmdir
from os.path import isdir, join

from qgis.core import QgsProcessingAlgorithm, QgsProcessingException
from qgis.core import QgsProcessingParameterFile, QgsProcessingParameterString

from qaequilibrae.i18n.translate import trlt


class CreateEmptyProject(QgsProcessingAlgorithm):
    PARENT_FOLDER = "PARENT_FOLDER"
    MODEL_NAME = "MODEL_NAME"

    # The model name becomes a folder name, so anything a file system could choke on is out
    INVALID_NAME_CHARACTERS = '\\/:*?"<>|'

    # These resolve to the parent folder itself (or above it) instead of a new folder inside it
    RESERVED_NAMES = (".", "..")

    def initAlgorithm(self, config=None):
        # 1. Existing folder the new model folder will be created in
        self.addParameter(
            QgsProcessingParameterFile(
                self.PARENT_FOLDER, self.tr("Parent folder"), behavior=QgsProcessingParameterFile.Folder
            )
        )

        # 2. Name of the model's own folder, created inside the parent folder
        self.addParameter(
            QgsProcessingParameterString(self.MODEL_NAME, self.tr("Model name"), defaultValue="new model")
        )

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

        # Caught before joining, since these would point the project folder at the parent folder
        # itself and leave the empty-folder handling below ready to remove it
        if model_name in self.RESERVED_NAMES:
            raise QgsProcessingException(self.tr("The model name cannot be '.' or '..'"))

        project_folder = join(parent_folder, model_name)

        # Checks if we have access to AequilibraE library
        if iutil.find_spec("aequilibrae") is None:
            raise QgsProcessingException(self.tr("AequilibraE module not found"))

        from aequilibrae.project import Project

        # AequilibraE refuses to create a project on a folder that already exists, so we
        # only clear the way when the folder we were pointed to is empty
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

        project.close()

        feedback.pushInfo(self.tr("Project created in ") + project_folder)
        feedback.pushInfo(self.tr("Default modes: ") + ", ".join(sorted(modes)))
        feedback.pushInfo(self.tr("Default link types: ") + ", ".join(sorted(link_types)))

        return {"Output": project_folder}

    def name(self):
        return "create_empty_project"

    def displayName(self) -> str:
        return self.tr("Create empty project")

    def group(self) -> str:
        return self.tr("Model building")

    def groupId(self) -> str:
        return "model_building"

    def shortHelpString(self):
        help_messages = [
            self.tr("Creates a new empty AequilibraE project, with no links, nodes or zones."),
            self.tr("The project is created with the default modes and link types, and can be"),
            self.tr("populated afterwards with the other Model building tools."),
            self.tr("The model is created in a folder named after the model, inside the parent"),
            self.tr("folder you choose. That model folder must not exist yet, or must be empty."),
        ]
        return "\n".join(help_messages)

    def createInstance(self):
        return CreateEmptyProject()

    def tags(self):
        return ["create", "new", "empty", "project", "model"]

    def tr(self, message):
        return trlt("CreateEmptyProject", message)

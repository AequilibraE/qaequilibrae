import importlib.util as iutil
from os import listdir, rmdir
from os.path import isdir

from qgis.core import QgsProcessingAlgorithm, QgsProcessingException
from qgis.core import QgsProcessingParameterFolderDestination

from qaequilibrae.i18n.translate import trlt


class CreateEmptyProject(QgsProcessingAlgorithm):

    PROJECT_FOLDER = "PROJECT_FOLDER"

    def initAlgorithm(self, config=None):
        # Folder that will hold the brand new AequilibraE project
        self.addParameter(
            QgsProcessingParameterFolderDestination(self.PROJECT_FOLDER, self.tr("New AequilibraE project folder"))
        )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.parameterAsString(parameters, self.PROJECT_FOLDER, context)

        # Checks if we have access to AequilibraE library
        if iutil.find_spec("aequilibrae") is None:
            raise QgsProcessingException(self.tr("AequilibraE module not found"))

        from aequilibrae.project import Project

        # AequilibraE refuses to create a project on a folder that already exists, so we
        # only clear the way when the folder we were pointed to is empty
        if isdir(project_folder):
            if listdir(project_folder):
                raise QgsProcessingException(self.tr("Folder already exists and is not empty: ") + project_folder)
            rmdir(project_folder)

        feedback.pushInfo(self.tr("Creating project"))

        project = Project()
        try:
            project.new(project_folder)
        except Exception as e:
            raise QgsProcessingException(self.tr("Could not create project: ") + str(e))

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
            self.tr("The folder you point to must not exist, or must be empty."),
        ]
        return "\n".join(help_messages)

    def createInstance(self):
        return CreateEmptyProject()

    def tags(self):
        return ["create", "new", "empty", "project", "model"]

    def tr(self, message):
        return trlt("CreateEmptyProject", message)

"""Add a mode to an AequilibraE project."""

from qgis.core import Qgis, QgsProcessingException, QgsProcessingParameterNumber, QgsProcessingParameterString

from ..project import open_project
from ..project_algorithm import ProjectAlgorithm


class AddMode(ProjectAlgorithm):
    group_name = "Data"
    group_id = "data"
    MODE_ID = "MODE_ID"
    MODE_NAME = "MODE_NAME"
    DESCRIPTION = "DESCRIPTION"
    PCE = "PCE"
    VOT = "VOT"
    PPV = "PPV"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(QgsProcessingParameterString(self.MODE_ID, self.tr("Mode ID")))
        self.addParameter(QgsProcessingParameterString(self.MODE_NAME, self.tr("Mode name")))
        self.addParameter(QgsProcessingParameterString(self.DESCRIPTION, self.tr("Description"), optional=True))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PCE,
                self.tr("Passenger car equivalent"),
                type=Qgis.ProcessingNumberParameterType.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.VOT, self.tr("Value of time"), type=Qgis.ProcessingNumberParameterType.Double, optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PPV, self.tr("Persons per vehicle"), type=Qgis.ProcessingNumberParameterType.Double, optional=True
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.project_folder(parameters, context)
        mode_id = self.parameterAsString(parameters, self.MODE_ID, context).strip()
        mode_name = self.parameterAsString(parameters, self.MODE_NAME, context).strip()
        if len(mode_id) != 1 or not mode_id.isascii() or not mode_id.isalpha():
            raise QgsProcessingException(self.tr("The mode ID must be a single ASCII letter"))
        if not mode_name:
            raise QgsProcessingException(self.tr("The mode name cannot be empty"))
        with open_project(project_folder) as project:
            mode = project.network.modes.new(mode_id)
            mode.mode_name = mode_name
            mode.description = self.parameterAsString(parameters, self.DESCRIPTION, context).strip() or None
            for parameter, field in ((self.PCE, "pce"), (self.VOT, "vot"), (self.PPV, "ppv")):
                if parameters.get(parameter) not in (None, ""):
                    setattr(mode, field, self.parameterAsDouble(parameters, parameter, context))
            project.network.modes.add(mode)
            mode.save()
        return {"MODE_ID": mode_id}

    def name(self):
        return "add_mode"

    def displayName(self):
        return self.tr("Add mode")

    def shortHelpString(self):
        return self.tr("Adds a mode to an AequilibraE project.")

    def createInstance(self):
        return AddMode()

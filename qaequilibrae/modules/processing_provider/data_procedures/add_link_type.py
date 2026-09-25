"""Add a link type to an AequilibraE project."""

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from ..project import open_project
from ..project_algorithm import ProjectAlgorithm


class AddLinkType(ProjectAlgorithm):
    group_name = "Data"
    group_id = "data"
    LINK_TYPE_ID = "LINK_TYPE_ID"
    LINK_TYPE = "LINK_TYPE"
    DESCRIPTION = "DESCRIPTION"
    LANES = "LANES"
    LANE_CAPACITY = "LANE_CAPACITY"
    SPEED = "SPEED"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(QgsProcessingParameterString(self.LINK_TYPE_ID, self.tr("Link type ID")))
        self.addParameter(QgsProcessingParameterString(self.LINK_TYPE, self.tr("Link type name")))
        self.addParameter(QgsProcessingParameterString(self.DESCRIPTION, self.tr("Description"), optional=True))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LANES, self.tr("Lanes"), type=Qgis.ProcessingNumberParameterType.Double, optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LANE_CAPACITY,
                self.tr("Lane capacity"),
                type=Qgis.ProcessingNumberParameterType.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SPEED, self.tr("Speed"), type=Qgis.ProcessingNumberParameterType.Double, optional=True
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.project_folder(parameters, context)
        type_id = self.parameterAsString(parameters, self.LINK_TYPE_ID, context).strip()
        name = self.parameterAsString(parameters, self.LINK_TYPE, context).strip()
        if len(type_id) != 1 or not type_id.isascii() or not type_id.isalpha():
            raise QgsProcessingException(self.tr("The link type ID must be a single ASCII letter"))
        if not name:
            raise QgsProcessingException(self.tr("The link type name cannot be empty"))
        with open_project(project_folder) as project:
            link_type = project.network.link_types.new(type_id)
            link_type.link_type = name
            link_type.description = self.parameterAsString(parameters, self.DESCRIPTION, context).strip() or None
            for parameter, field in (
                (self.LANES, "lanes"),
                (self.LANE_CAPACITY, "lane_capacity"),
                (self.SPEED, "speed"),
            ):
                if parameters.get(parameter) not in (None, "") and field in link_type.__dict__:
                    setattr(link_type, field, self.parameterAsDouble(parameters, parameter, context))
            link_type.save()
        return {"LINK_TYPE_ID": type_id}

    def name(self):
        return "add_link_type"

    def displayName(self):
        return self.tr("Add link type")

    def shortHelpString(self):
        return self.tr("Adds a link type to an AequilibraE project.")

    def createInstance(self):
        return AddLinkType()

"""Add a link type to an AequilibraE project."""

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from ..project import borrow_project
from ..project_algorithm import ProjectAlgorithm


class AddLinkType(ProjectAlgorithm):
    algorithm_name = "add_link_type"
    display_name = "Add link type"
    group_name = "Data"
    group_id = "data"

    LINK_TYPE_ID = "LINK_TYPE_ID"
    LINK_TYPE = "LINK_TYPE"
    DESCRIPTION = "DESCRIPTION"
    LANES = "LANES"
    LANE_CAPACITY = "LANE_CAPACITY"
    SPEED = "SPEED"
    project = None

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
        self.addParameter(QgsProcessingParameterString(self.LINK_TYPE_ID, self.tr("Link type ID")))
        self.addParameter(QgsProcessingParameterString(self.LINK_TYPE, self.tr("Link type name")))
        self.addParameter(QgsProcessingParameterString(self.DESCRIPTION, self.tr("Description"), optional=True))
        for key, label in (
            (self.LANES, "Lanes"),
            (self.LANE_CAPACITY, "Lane capacity"),
            (self.SPEED, "Speed"),
        ):
            self.addParameter(
                QgsProcessingParameterNumber(
                    key, self.tr(label), type=Qgis.ProcessingNumberParameterType.Double, optional=True
                )
            )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = self.project or self.project_folder(parameters, context)
        type_id = self.parameterAsString(parameters, self.LINK_TYPE_ID, context).strip()
        name = self.parameterAsString(parameters, self.LINK_TYPE, context).strip()
        if len(type_id) != 1 or not type_id.isascii() or not type_id.isalpha():
            raise QgsProcessingException(self.tr("The link type ID must be a single ASCII letter"))
        if not name:
            raise QgsProcessingException(self.tr("The link type name cannot be empty"))
        with borrow_project(project_folder) as project:
            link_types = project.network.link_types
            link_type = link_types.new(type_id)
            try:
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
            except Exception:
                try:
                    link_types.delete(type_id)
                except Exception:
                    link_types.all_types().pop(type_id, None)
                raise
        return {"LINK_TYPE_ID": type_id}

    def shortHelpString(self):
        return self.tr("Adds a link type to an AequilibraE project.")

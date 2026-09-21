from qgis.core import QgsProcessingParameterDefinition

from aequilibrae.project import Project

class QgsProcessingParameterAequilibraeProject(QgsProcessingParameterDefinition):

    def __init__(self, name: str | None = None, description: str | None = '', project: None | Project = None):
        self.project = project
        super().__init__(name=name, description=description)

    def type():
        return Project

    def clone():
        return QgsProcessingParameterAequilibraeProject()

    def getProject():
        # FIXME: is this the best way? Is the return mutable?
        return self.project

    def close():
        if self.project is None:
            return
        self.project.close()

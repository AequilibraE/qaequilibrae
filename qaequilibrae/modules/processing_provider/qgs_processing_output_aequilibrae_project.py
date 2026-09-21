from qgis.core import QgsProcessingOutputDefinition

from aequilibrae.project import Project

class QgsProcessingOutputAequilibraeProject(QgsProcessingOutputDefinition):

    def __init__(name: str | None = None, description: str | None = '', project: None | Project = None):
        self.project = project
        super.__init__(name, description)

    def type():
        return Project

    def getProject():
        # FIXME: is this the best way? Is the return mutable?
        return self.project

    def closeProject():
        if self.project is None:
            return
        self.project.close()
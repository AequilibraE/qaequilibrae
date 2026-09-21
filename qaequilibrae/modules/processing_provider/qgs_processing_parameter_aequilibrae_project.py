from qgis.core import QgsProcessingParameterDefinition

from aequilibrae.project import Project

class QgsProcessingParameterAequilibraeProject(QgsProcessingParameterDefinition):

    def __init__(project, **kwargs):
        self.project = project
        super.__init__(**kwargs)

    def clone():
        return QgsProcessingParameterAequilibraeProject(self.project)

    def type():
        return Project

    def getProject():
        # FIXME: is this the best way? Should some form of clone be used? What's
        return self.project
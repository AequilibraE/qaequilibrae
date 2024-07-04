import importlib.util as iutil
import sys

from qgis.core import QgsProcessingMultiStepFeedback, QgsProcessingAlgorithm
from qgis.core import QgsProcessingParameterFile, QgsProcessingParameterNumber, QgsProcessingParameterString

from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.i18n.translate import trlt


class AddConnectors(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterNumber(
                "num_connectors",
                self.tr("Connectors per centroid"),
                type=QgsProcessingParameterNumber.Integer,
                minValue=1,
                maxValue=10,
                defaultValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "mode", self.tr("Modes to connect (only one at a time)"), multiLine=False, defaultValue="c"
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "project_path",
                self.tr("Project path"),
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=standard_path(),
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae import Project

        feedback.pushInfo(self.tr("Opening project"))
        project = Project()
        project.open(parameters["project_path"])

        nodes = project.network.nodes
        centroids = nodes.data
        centroids = centroids.loc[centroids["is_centroid"] == 1]

        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)

        # Adding connectors
        num_connectors = parameters["num_connectors"]
        mode = parameters["mode"]
        feedback.pushInfo(self.tr('Adding {} connectors when none exists for mode "{}"').format(num_connectors, mode))

        for _, node in centroids.iterrows():
            cnt = nodes.get(node.node_id)
            cnt.connect_mode(cnt.geometry.buffer(0.01), mode_id=mode, connectors=num_connectors)

        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        project.close()

        return {"Output": parameters["project_path"]}

    def name(self):
        return self.tr("Add centroid connectors")

    def displayName(self):
        return self.tr("Add centroid connectors")

    def group(self):
        return ("01-"+self.tr("Model Building"))

    def groupId(self):
        return ("01-"+self.tr("Model Building"))

    def shortHelpString(self):
        return self.tr("Go through all the centroids and add connectors only if none exists for the chosen mode")

    def createInstance(self):
        return AddConnectors()

    def tr(self, message):
        return trlt("AddConnectors", message)

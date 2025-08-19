import importlib.util as iutil
import sys

from qgis.core import (
    QgsProcessingMultiStepFeedback,
    QgsProcessingAlgorithm,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.common_tools import polygon_from_radius


class AddConnectors(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "project_path", self.tr("Project path"), behavior=QgsProcessingParameterFile.Folder
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "num_connectors",
                self.tr("Number of connectors per centroid"),
                type=QgsProcessingParameterNumber.Integer,
                minValue=1,
                defaultValue=1,
            )
        )

        advparams = [
            QgsProcessingParameterString(
                "mode", self.tr("Modes to connect (defaults to all)"), multiLine=False, optional=True
            ),
            QgsProcessingParameterString(
                "link_type", self.tr("Link types to connect (defaults to all)"), multiLine=False, optional=True
            ),
        ]

        for param in advparams:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae import Project

        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)
        feedback.pushInfo(self.tr("Opening project"))

        project = Project()
        project.open(parameters["project_path"])

        nodes = project.network.nodes
        nodes.refresh()

        centroids = nodes.data[nodes.data["is_centroid"] == 1].node_id.tolist()

        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)

        # Adding connectors
        feedback.pushInfo(self.tr("Adding centroid connectors"))

        lt = project.network.link_types.all_types()
        link_types = parameters["link_type"] if "link_type" in parameters else "".join(lt.keys())

        modes = project.network.modes.all_modes()
        modes = list(set(parameters["mode"])) if "mode" in parameters else [k for k in modes.keys()]

        for counter, zone_id in enumerate(centroids):
            node = nodes.get(zone_id)
            geo = polygon_from_radius(node.geometry, 3000)
            for mode_id in modes:
                node.connect_mode(
                    area=geo, mode_id=mode_id, link_types=link_types, connectors=parameters["num_connectors"]
                )

        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        project.network.nodes.refresh()
        project.network.links.refresh()
        project.close()

        return {"Output": parameters["project_path"]}

    def name(self):
        return "addcentroidconnector"

    def displayName(self):
        return self.tr("Add centroid connectors")

    def group(self):
        return self.tr("1. Model Building")

    def groupId(self):
        return "modelbuilding"

    def shortHelpString(self):
        return self.tr("Adds centroid connectors for one or all modes.")

    def createInstance(self):
        return AddConnectors()

    def tr(self, message):
        return trlt("AddConnectors", message)

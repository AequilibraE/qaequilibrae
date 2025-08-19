from aequilibrae.context import get_logger
from qgis.core import QgsProcessingAlgorithm, QgsMessageLog, QgsProcessingParameterString
from qgis.core import QgsProcessingParameterEnum
from qgis.utils import plugins

from qaequilibrae.i18n.translate import trlt


class RunProcedures(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        try:
            # Attempt to retrieve the AequilibraE plugin instance
            aeq_plugin = plugins.get("qaequilibrae")

            if not aeq_plugin:
                self.addParameter(
                    QgsProcessingParameterString(
                        "PROJECT_INFO", self.tr("No AequilibraE project loaded."), optional=True
                    )
                )
                return
            else:
                self.project = aeq_plugin.project

            # Check if there's an open project and fetch its information
            if self.project:
                self.items = list(self.project.run._fields)
                self.addParameter(
                    QgsProcessingParameterEnum(
                        "available_funcs",
                        self.tr("Available functions"),
                        self.items,
                        defaultValue=0,
                    )
                )
            else:
                self.addParameter(
                    QgsProcessingParameterString(
                        "PROJECT_INFO", self.tr("No AequilibraE project loaded."), optional=True
                    )
                )

        except Exception as e:
            # Handle cases where the plugin or project information is not accessible
            QgsMessageLog.logMessage(f"Error checking AequilibraE project: {str(e)}")

    def processAlgorithm(self, parameters, context, feedback):
        feedback.pushInfo("Get logger")
        logger = get_logger()

        feedback.pushInfo("Run")
        idx = parameters["available_funcs"]
        func_name = self.items[idx]

        func = getattr(self.project.run, func_name)
        result = func()
        logger.info(result)

        return {"Output": "Success: Check logfile for details"}

    def name(self):
        return "runprocedures"

    def displayName(self):
        return self.tr("Run procedures")

    def group(self):
        return self.tr("1. Model Building")

    def groupId(self):
        return "modelbuilding"

    def shortHelpString(self):
        return self.tr("Run entire model pipelines from AequilibraE")

    def createInstance(self):
        return RunProcedures()

    def tr(self, message):
        return trlt("RunProcedures", message)

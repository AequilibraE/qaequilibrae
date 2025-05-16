import importlib.util as iutil
import sys

from qgis.core import QgsProcessingParameterEnum, QgsProcessingParameterFile
from qgis.core import QgsProcessingAlgorithm, QgsMessageLog, QgsProcessingParameterString

from qaequilibrae.i18n.translate import trlt


class TripLengthDistribution(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        """
        Define parameters and outputs of the algorithm and attempt to load information
        from an open AequilibraE project (if available).
        """
        from qgis.utils import plugins

        # Initialize parameters for the algorithm
        try:
            # Attempt to retrieve the AequilibraE plugin instance
            aeq_plugin = plugins.get("qaequilibrae")

            if not aeq_plugin:
                self.aequilibrae_info = None
                self.addParameter(
                    QgsProcessingParameterString(
                        "PROJECT_INFO", self.tr("No AequilibraE project loaded."), optional=True
                    )
                )
                return

            # Check if there's an open project and fetch its information
            self.project = aeq_plugin.project
            if self.project:
                self.matrices = self.project.matrices
                mat_names = self.matrices.list()["name"].tolist()

                self.addParameter(
                    QgsProcessingParameterEnum(
                        "demand_mat_name",
                        self.tr("Demand matrix"),
                        mat_names,
                        defaultValue=0,  # Default to the first option
                    )
                )

                self.addParameter(
                    QgsProcessingParameterString(
                        "demand_mat_core",
                        self.tr("Demand matrix core"),
                        multiLine=False,
                    )
                )
                self.addParameter(
                    QgsProcessingParameterEnum(
                        "skim_mat_name",
                        self.tr("Skim matrix"),
                        mat_names,
                        defaultValue=0,  # Default to the first option
                    )
                )
                self.addParameter(
                    QgsProcessingParameterString(
                        "skim_mat_core",
                        self.tr("Skim matrix core"),
                        multiLine=False,
                    )
                )
                self.addParameter(
                    QgsProcessingParameterFile(
                        "file_path",
                        self.tr("File path"),
                        behavior=QgsProcessingParameterFile.Folder,
                    )
                )
            else:
                self.aequilibrae_info = None
                self.addParameter(
                    QgsProcessingParameterString(
                        "PROJECT_INFO", self.tr("No AequilibraE project loaded."), optional=True
                    )
                )

        except Exception as e:
            # Handle cases where the plugin or project information is not accessible
            QgsMessageLog.logMessage(f"Error checking AequilibraE project: {str(e)}")

    def checkParameterValues(self, parameters, context):
        """
        Check if parameter values are valid before running the algorithm.
        This function also updates the secondary options when the primary selection changes.
        """
        # Check if the demand matrix has the indicated demand matrix core
        self.demand_matrix = self.matrices.get_matrix(parameters["demand_mat_name"])
        demand_cores = self.demand_matrix.names
        if parameters["demand_mat_core"] not in demand_cores:
            return False, "Core does not exist at the selected matrix."

        # Check if the skim matrix has the indicated skim matrix core
        self.skim_matrix = self.matrices.get_matrix(parameters["skim_mat_name"])
        skim_cores = self.skim_matrix.names
        if parameters["skim_mat_core"] not in skim_cores:
            return False, "Core does not exist at the selected matrix."

        return True, ""

    def processAlgorithm(self, parameters, context, feedback):
        # Checks if we have AequilibraE installed
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        import matplotlib.pyplot as plt

    def name(self):
        return self.tr("Trip length distribution")

    def displayName(self) -> str:
        return self.tr("Trip length distribution")

    def group(self) -> str:
        return self.tr("2. Data")

    def groupId(self) -> str:
        return "data"

    def shortHelpString(self):
        return self.tr("Creates a trip-length distribution histogram and save in an output folder.")

    def createInstance(self):
        return TripLengthDistribution()

    def tr(self, message):
        return trlt("TripLengthDistribution", message)

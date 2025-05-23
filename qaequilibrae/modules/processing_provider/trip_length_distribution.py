import importlib.util as iutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from qgis.core import QgsProcessingAlgorithm, QgsMessageLog, QgsProcessingParameterString
from qgis.core import QgsProcessingParameterEnum, QgsProcessingParameterFileDestination
from qgis.utils import plugins

from qaequilibrae.i18n.translate import trlt


class TripLengthDistribution(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        """
        Define parameters and outputs of the algorithm and attempt to load information
        from an open AequilibraE project (if available).
        """
        # Initialize parameters for the algorithm
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
                self.matrices = self.project.matrices
                self.mat_names = self.matrices.list()["name"].tolist()

                self.addParameter(
                    QgsProcessingParameterEnum(
                        "demand_mat_name",
                        self.tr("Demand matrix"),
                        self.matrices.list()["name"].tolist(),
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
                        self.matrices.list()["name"].tolist(),
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
                    QgsProcessingParameterFileDestination(
                        "file_path",
                        self.tr("File path"),
                        fileFilter="PNG (*.png)",
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
        # Checks if we have AequilibraE installed
        if iutil.find_spec("aequilibrae") is None:
            feedback.reportError(self.tr("AequilibraE module not found"))
            return {"Output": "Error: AequilibraE module not found"}

        # Check if the demand matrix has the indicated demand matrix core
        demand_mat_idx = parameters["demand_mat_name"]
        demand_mat_core = parameters["demand_mat_core"]

        demand_matrix = self.matrices.get_matrix(self.mat_names[demand_mat_idx])
        demand_cores = demand_matrix.names

        if demand_mat_core in demand_cores:
            demand_matrix.computational_view([demand_mat_core])
            feedback.pushInfo("Successfully set computational view for demand matrix")
        else:
            feedback.reportError(f"Demand matrix core '{demand_mat_core}' not found in available cores: {demand_cores}")
            return {"Output": f"Error: Demand matrix core '{demand_mat_core}' not found"}

        # Check if the skim matrix has the indicated skim matrix core
        skim_mat_idx = parameters["skim_mat_name"]
        skim_mat_core = parameters["skim_mat_core"]

        skim_matrix = self.matrices.get_matrix(self.mat_names[skim_mat_idx])
        skim_cores = skim_matrix.names

        if skim_mat_core in skim_cores:
            skim_matrix.computational_view([skim_mat_core])
            feedback.pushInfo("Successfully set computational view for skim matrix")
        else:
            feedback.reportError(f"Skim matrix core '{skim_mat_core}' not found in available cores: {skim_cores}")
            return {"Output": f"Error: Skim matrix core '{skim_mat_core}' not found"}

        # Get plot data
        x_axis, y_axis = self.get_data(skim_matrix, demand_matrix)

        # Draw plot

        _, ax = plt.subplots(figsize=(10, 6))

        plt.plot(x_axis, y_axis)
        ax.set(title="Trip length distribution")
        ax.set_xlabel("Trip length (km)")
        ax.set_ylabel("Trips")

        plt.savefig(parameters["file_path"])
        plt.close()

        return {"Output": f"Success: TLD plot saved in {parameters['file_path']}"}

    def get_data(self, skim, demand):
        from scipy.interpolate import make_interp_spline

        max_bins = int(np.ceil(skim.matrix_view.max()))
        y, x = np.histogram((demand.matrix_view * skim.matrix_view) / 1000, bins=np.arange(0, max_bins))
        df = pd.DataFrame({"distance": x[1:], "trips": y})

        x_axis = np.linspace(df["distance"].min(), df["distance"].max(), 300)
        spline = make_interp_spline(df["distance"], y, k=3)
        y_axis = spline(x_axis)
        return x_axis, y_axis

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

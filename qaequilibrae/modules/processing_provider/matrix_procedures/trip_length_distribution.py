from math import ceil, floor, log10

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt

from ..geometry_io.project import open_project


class TripLengthDistribution(QgsProcessingAlgorithm):
    PROJECT_FOLDER = "PROJECT_FOLDER"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECT_FOLDER,
                self.tr("AequilibraE project folder"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )
        self.addParameter(QgsProcessingParameterString("demand_mat_name", self.tr("Demand matrix")))
        self.addParameter(QgsProcessingParameterString("demand_mat_core", self.tr("Demand matrix core")))
        self.addParameter(QgsProcessingParameterString("skim_mat_name", self.tr("Skim matrix")))
        self.addParameter(QgsProcessingParameterString("skim_mat_core", self.tr("Skim matrix core")))
        self.addParameter(QgsProcessingParameterString("plot_name", self.tr("Plot name"), optional=True))
        self.addParameter(
            QgsProcessingParameterFileDestination(
                "file_path",
                self.tr("File path"),
                fileFilter="PNG (*.png)",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        project_folder = (
            self.parameterAsFile(parameters, self.PROJECT_FOLDER, context) if self.PROJECT_FOLDER in parameters else None
        )
        if project_folder:
            with open_project(project_folder) as project:
                self.matrices = project.matrices
                self.mat_names = self.matrices.list()["name"].tolist()
                return self._process_algorithm(parameters, context, feedback)

        # Keep direct callers that inject matrices working while the Processing
        # interface uses an explicit project folder.
        if not hasattr(self, "matrices") or not hasattr(self, "mat_names"):
            raise QgsProcessingException(self.tr("An AequilibraE project folder is required"))
        return self._process_algorithm(parameters, context, feedback)

    def _process_algorithm(self, parameters, context, feedback):
        """Create the plot while the project-owned matrix handles are alive."""

        # Check if the demand matrix has the indicated demand matrix core
        demand_mat_idx = parameters["demand_mat_name"]
        demand_mat_core = parameters["demand_mat_core"]

        demand_matrix = self.matrices.get_matrix(self._matrix_name(demand_mat_idx))
        demand_cores = demand_matrix.names

        if demand_mat_core in demand_cores:
            demand_matrix.computational_view([demand_mat_core])
            feedback.pushInfo("Successfully set computational view for demand matrix")
        else:
            feedback.reportError(f"Demand matrix core {demand_mat_core!r} not found in available cores: {demand_cores}")
            return {"Output": f"Error: Demand matrix core {demand_mat_core!r} not found"}

        # Check if the skim matrix has the indicated skim matrix core
        skim_mat_idx = parameters["skim_mat_name"]
        skim_mat_core = parameters["skim_mat_core"]

        skim_matrix = self.matrices.get_matrix(self._matrix_name(skim_mat_idx))
        skim_cores = skim_matrix.names

        if skim_mat_core in skim_cores:
            skim_matrix.computational_view([skim_mat_core])
            feedback.pushInfo("Successfully set computational view for skim matrix")
        else:
            feedback.reportError(f"Skim matrix core {skim_mat_core!r} not found in available cores: {skim_cores}")
            return {"Output": f"Error: Skim matrix core {skim_mat_core!r} not found"}

        plt_name = parameters["plot_name"] if "plot_name" in parameters else "Trip length distribution"

        # Draw plot
        mult = floor(skim_matrix.index.shape[0] / 10)
        b = max(1, floor(log10(skim_matrix.matrix_view.shape[0]) * mult))
        n, bins, _ = plt.hist(
            np.nan_to_num(skim_matrix.matrix_view.flatten(), nan=0),
            bins=b,
            weights=np.nan_to_num(demand_matrix.matrix_view.flatten()),
            density=False,
            facecolor="#146DB3",
            alpha=0.75,
        )

        df = pd.DataFrame([n[1:], bins[1:]]).transpose().fillna(0)
        df.columns = ["trips", "position"]
        df["cumsum"] = df["trips"].cumsum()
        df["rate"] = df["cumsum"] / df["trips"].sum()
        if df["rate"].min() == df["rate"].max():
            limit_right = ceil(df["position"].values[-1])
        else:
            limit_right = ceil(df[df["rate"] <= 0.99]["position"].values[-1])

        ax = plt.gca()
        ax.set_xlim(left=0, right=limit_right)
        ax.set_ylim(bottom=0, top=ceil(max(n[1:]) * 1.1))
        plt.xlabel("Trip length")
        plt.ylabel("Trips")
        plt.title(plt_name)

        plt.savefig(parameters["file_path"])
        plt.close()

        return {"Output": f"Success: TLD plot saved in {parameters['file_path']}"}

    def _matrix_name(self, value):
        """Accept matrix names and the old enum indexes for direct callers."""
        if isinstance(value, int):
            return self.mat_names[value]
        return str(value)

    def name(self):
        return self.tr("Trip length distribution")

    def displayName(self) -> str:
        return self.tr("Trip length distribution")

    def group(self) -> str:
        return self.tr("Data")

    def groupId(self) -> str:
        return "data"

    def shortHelpString(self):
        return self.tr("Creates a trip-length distribution histogram and save in an output folder.")

    def createInstance(self):
        return TripLengthDistribution()

    def tr(self, message):
        return trlt("TripLengthDistribution", message)

from contextlib import ExitStack
from math import ceil, floor, log10

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from ..project import borrow_project
from ..project_algorithm import ProjectAlgorithm


class TripLengthDistribution(ProjectAlgorithm):
    algorithm_name = "Trip length distribution"
    display_name = "Trip length distribution"
    translate_algorithm_name = True
    group_name = "Data"
    group_id = "data"

    def initAlgorithm(self, configuration=None):
        self.add_project_folder_parameter()
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
        with ExitStack() as resources:
            if self.PROJECT_FOLDER in parameters:
                project = resources.enter_context(borrow_project(self.project_folder(parameters, context)))
                matrices = project.matrices
                mat_names = matrices.list()["name"].tolist()
            else:
                # Legacy direct callers inject a matrix manager and use enum indexes.
                if not hasattr(self, "matrices") or not hasattr(self, "mat_names"):
                    raise QgsProcessingException(self.tr("An AequilibraE project folder is required"))
                matrices, mat_names = self.matrices, self.mat_names

            selected = {}
            for kind in ("demand", "skim"):
                name = parameters[f"{kind}_mat_name"]
                matrix = matrices.get_matrix(mat_names[name] if isinstance(name, int) else str(name))
                resources.callback(matrix.close)
                core = parameters[f"{kind}_mat_core"]
                if core not in matrix.names:
                    feedback.reportError(
                        f"{kind.title()} matrix core {core!r} not found in available cores: {matrix.names}"
                    )
                    return {"Output": f"Error: {kind.title()} matrix core {core!r} not found"}
                matrix.computational_view([core])
                feedback.pushInfo(f"Successfully set computational view for {kind} matrix")
                selected[kind] = matrix
            demand_matrix, skim_matrix = selected["demand"], selected["skim"]

            figure, axis = plt.subplots()
            resources.callback(plt.close, figure)
            zone_scale = floor(skim_matrix.index.shape[0] / 10)
            bin_count = max(1, floor(log10(skim_matrix.matrix_view.shape[0]) * zone_scale))
            counts, bin_edges, _ = axis.hist(
                np.nan_to_num(skim_matrix.matrix_view.flatten(), nan=0),
                bins=bin_count,
                weights=np.nan_to_num(demand_matrix.matrix_view.flatten()),
                density=False,
                facecolor="#146DB3",
                alpha=0.75,
            )

            histogram = pd.DataFrame([counts[1:], bin_edges[1:]]).transpose().fillna(0)
            histogram.columns = ["trips", "position"]
            histogram["cumsum"] = histogram["trips"].cumsum()
            histogram["rate"] = histogram["cumsum"] / histogram["trips"].sum()
            if histogram["rate"].min() == histogram["rate"].max():
                limit_right = ceil(histogram["position"].values[-1])
            else:
                limit_right = ceil(histogram[histogram["rate"] <= 0.99]["position"].values[-1])

            axis.set_xlim(left=0, right=limit_right)
            axis.set_ylim(bottom=0, top=ceil(max(counts[1:]) * 1.1))
            axis.set_xlabel("Trip length")
            axis.set_ylabel("Trips")
            axis.set_title(parameters.get("plot_name", "Trip length distribution"))
            figure.savefig(parameters["file_path"])

        return {"Output": f"Success: TLD plot saved in {parameters['file_path']}"}

    def shortHelpString(self):
        return self.tr("Creates a trip-length distribution histogram in the output folder.")

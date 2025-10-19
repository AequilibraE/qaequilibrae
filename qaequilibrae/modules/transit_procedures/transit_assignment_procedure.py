import numpy as np
from qgis.PyQt.QtCore import pyqtSignal
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import TransitAssignment, TransitClass
from aequilibrae.transit.transit_graph_builder import TransitGraphBuilder
from aequilibrae.utils.interface.worker_thread import WorkerThread


class TransitAssignProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, project, transit_data, configs, action):
        WorkerThread.__init__(self, parentThread)
        self.project = project
        self.transit_data = transit_data
        self.configs = configs
        self.action = action

    def doWork(self):
        self.signal.emit(["start", 10, "Start procedure"])
        self.build_graph()

        self.mat = self.build_matrix()

        self.build_assignment()
        self.signal.emit(["finished"])

    def build_graph(self):
        if not self.configs["has_graph"]:
            self.signal.emit(["update", 1, "Creating graph builder"])
            graph = self.transit_data.create_graph(
                period_id=self.configs["period_id"],
                with_outer_stop_transfers=self.configs["with_outer_stop_transfers"],
                with_inner_stop_transfers=self.configs["with_inner_stop_transfers"],
                with_walking_edges=self.configs["with_walking_edges"],
                blocking_centroid_flows=self.configs["blocking_centroid_flows"],
                connector_method=self.configs["connector_method"],
            )

            self.signal.emit(["update", 2, "Building network graphs"])
            self.project.network.build_graphs()

            self.signal.emit(["update", 3, "Creating line geometry"])
            graph.create_line_geometry(method=self.configs["line_method"], graph=self.configs["mode_id"])

            if self.configs["save_graph"]:
                self.signal.emit(["update", 4, "Saving graph"])
                self.transit_data.save_graphs(period_ids=[self.configs["period_id"]])

        else:
            self.signal.emit(["update", 3, "Reloading graph into project"])

            graph = TransitGraphBuilder.from_db(self.project, self.configs["period_id"])

        # To perform an assignment we need to convert the graph builder into a graph.
        self.signal.emit(["update", 5, "Convert into graph"])
        self.transit_graph = graph.to_transit_graph()

    def build_matrix(self):
        if self.action == "create":
            self.signal.emit(["update", 6, "Creating ones matrix"])
            zones = len(self.transit_graph.centroids)

            mat = AequilibraeMatrix()
            mat.create_empty(zones=zones, matrix_names=["pt"], memory_only=True)
            mat.index[:] = self.transit_graph.centroids[:]
            mat.matrices[:, :, 0] = np.ones((zones, zones))
            mat.computational_view()

        elif self.action == "assign":
            self.signal.emit(["update", 6, "Loading matrix"])
            mat_name = self.configs["mat_name"]

            mat = self.project.matrices.get_matrix(mat_name)
            if not np.array_equal(mat.index, self.transit_graph.centroids):
                mat.index[:] = self.transit_graph.centroids  # ensure we have the same centroids
            mat.computational_view(self.configs["mat_core"])

        return mat

    def build_assignment(self):
        # Create the Transit Class
        self.signal.emit(["update", 7, "Creating Transit Class"])
        assigclass = TransitClass(name=self.configs["class_name"], graph=self.transit_graph, matrix=self.mat)

        # Create the Transit Assignment Class
        self.signal.emit(["update", 8, "Creating Transit Assignment object"])
        assig = TransitAssignment()
        assig.add_class(assigclass)

        # Set assignment
        assig.set_time_field(self.configs["time_field"])
        assig.set_frequency_field(self.configs["frequency_field"])
        if self.action == "create":
            assig.set_skimming_fields(self.configs["skim_fields"])
        assig.set_algorithm("os")  # default value
        assigclass.set_demand_matrix_core(self.configs["demand_matrix_core"])

        # Perform the assignment
        self.signal.emit(["update", 9, "Execute Transit Assignment"])
        assig.execute()

        if self.action == "create":
            self.signal.emit(["update", 10, "Saving skimming results"])
            assig.get_skim_results()["pt"].export(
                self.project.project_base_path / "matrices" / f"{self.configs["matrix_name"]}.omx"
            )
        else:
            self.signal.emit(["update", 10, "Saving results"])
            assig.save_results(table_name=self.configs["result_name"])

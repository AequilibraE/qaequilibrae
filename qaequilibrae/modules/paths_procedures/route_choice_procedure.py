import os

import numpy as np
from PyQt5.QtCore import pyqtSignal
from aequilibrae.paths import RouteChoice, SubAreaAnalysis
from aequilibrae.utils.interface.worker_thread import WorkerThread

from qaequilibrae.modules.paths_procedures.plot_route_choice import plot_results
from qaequilibrae.modules.paths_procedures.execute_single_dialog import VisualizeSingle


class RouteChoiceProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, job, graph, parameters):
        WorkerThread.__init__(self, parentThread)
        self.job = job
        self.parameters = parameters
        self.graph = graph
        self.matrix = None

    def doWork(self):
        if self.job == "execute_single":
            self.do_execute_single()
        if self.job in ["assign", "build"]:
            self.do_assign_or_build()

        self.signal.emit(["finished"])

    def do_execute_single(self):
        node_from = self.parameters["node_from"]
        node_to = self.parameters["node_to"]
        demand = self.parameters["demand"]

        nodes_of_interest = np.array([node_from, node_to], dtype=np.int64)
        self._setup_graph(nodes_of_interest)

        self.rc = self._build_rc(self.graph)
        _ = self.rc.execute_single(node_from, node_to, float(demand))

        plot_results(self.rc.get_results().to_pandas(), node_from, node_to, self.link_layer)

    def do_assign_or_build(self):
        self._setup_graph(self.graph.centroids)

        if self.parameters["set_sub_area"]:
            sub_area = SubAreaAnalysis(self.graph, self.parameters["zones"], self.matrix)
            sub_area.rc.set_choice_set_generation(self.__algo, **self.parameters)
            sub_area.rc.execute(perform_assignment=True)

            # I don't know why but origin and destination ID are assumed to be strings, which is
            # raising an error when assembling the COO Matrix. We use infer objects to ensure that
            # indexes are numeric integers
            self.matrix = sub_area.post_process().reset_index().infer_objects()
            self.matrix = self.matrix.groupby(["origin id", "destination id"]).sum()

            # Rebuild graph for external ODs
            new_centroids = np.unique(self.matrix.reset_index()[["origin id", "destination id"]].to_numpy().reshape(-1))
            self.graph.prepare_graph(new_centroids)
            self.graph.set_graph("utility")

        self.rc = self._build_rc(self.graph)
        self.rc.add_demand(self.matrix)
        self.rc.prepare()

        if self.parameters["set_select_links"]:
            self.rc.set_select_links(self.parameters["select_links"])

        if self.job == "build" or self.parameters["save_choice_sets"]:
            folder = self.__check_folder_exists()
            self.rc.set_save_routes(folder)

        assig = True if self.job == "assign" else False

        self.rc.execute(assig)

    def _setup_graph(self, nodes_of_interest):
        self.graph.prepare_graph(nodes_of_interest)
        self.graph.set_graph("utility")

    def _build_rc(self, graph):
        kwargs = {}

        rc = RouteChoice(graph)
        rc.set_choice_set_generation(self.__algo, **kwargs)  # FIX
        return rc

    def __check_folder_exists(self):
        rc_folder = os.path.join(self.project.project_base_path, "route_choice")
        if not os.path.isdir(rc_folder):
            os.mkdir(rc_folder)
        return rc_folder

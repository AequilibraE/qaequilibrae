import numpy as np
from PyQt5.QtCore import pyqtSignal
from aequilibrae.paths import RouteChoice, SubAreaAnalysis
from aequilibrae.utils.interface.worker_thread import WorkerThread


class RouteChoiceProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, aeq_project, job, parameters):
        WorkerThread.__init__(self, parentThread)
        self.project = aeq_project
        self.job = job
        self.parameters = parameters
        self.matrix = parameters["matrix"]

        self.graph = None

    def doWork(self):
        self._configure_graph()

        if self.job == "execute_single":
            self.do_execute_single()
        if self.job in ["assign", "build"]:
            self.do_assign_or_build()

        self.signal.emit(["finished"])

    def do_execute_single(self):
        node_from = self.parameters["node_from"]
        node_to = self.parameters["node_to"]

        nodes_of_interest = np.array([node_from, node_to], dtype=np.int64)
        self.graph.prepare_graph(nodes_of_interest)
        self.graph.set_graph("utility")

        self.rc = self._build_rc(self.graph)
        _ = self.rc.execute_single(node_from, node_to, self.matrix)

    def do_assign_or_build(self):
        self.graph.prepare_graph(self.graph.centroids)
        self.graph.set_graph("utility")

        if self.parameters["set_sub_area"]:
            sub_area = SubAreaAnalysis(self.graph, self.parameters["zones"], self.matrix)
            sub_area.rc.set_choice_set_generation(self.parameters["algorithm"], **self.parameters["kwargs"])
            sub_area.rc.execute(True)

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
            self.rc.set_save_routes(self.parameters["rc_folder"])

        assig = True if self.job == "assign" else False

        self.rc.execute(assig)

    def _build_rc(self, graph):
        rc = RouteChoice(graph)
        rc.set_choice_set_generation(self.parameters["algorithm"], **self.parameters["kwargs"])
        return rc

    def _configure_graph(self):
        mode_id = self.parameters["graph"]["mode_id"]
        if mode_id not in self.project.network.graphs:
            self.project.network.build_graphs(modes=[mode_id])

        self.graph = self.project.network.graphs[mode_id]

        field = np.zeros((1, self.graph.network.shape[0]))
        for idx, (par, col) in enumerate(self.parameters["graph"]["utility"]):
            field += par * self.graph.network[col].array

        self.graph.network = self.graph.network.assign(utility=0)
        self.graph.network["utility"] = field.reshape(self.graph.network.shape[0], 1)

        if self.parameters["graph"]["use_chosen_links"]:
            self.graph = self.project.network.graphs.pop(mode_id)
            self.graph.exclude_links(self.parameters["graph"]["links_to_remove"])

        self.graph.set_blocked_centroid_flows(self.parameters["graph"]["block_centroid_flows"])

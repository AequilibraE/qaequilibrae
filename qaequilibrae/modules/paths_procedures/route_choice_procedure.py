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

        self.graph = parameters["graph"]

    def doWork(self):
        if self.job == "execute_single":
            self.do_execute_single()
        if self.job in ["assign", "build"]:
            self.do_assign_or_build()

        self.signal.emit(["finished"])

    def do_execute_single(self):
        self.rc = self._build_rc(self.graph)
        _ = self.rc.execute_single(self.parameters["node_from"], self.parameters["node_to"], self.matrix)

    def do_assign_or_build(self):
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
            self.graph.set_graph("__utility__")

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

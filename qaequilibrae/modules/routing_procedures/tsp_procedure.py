from PyQt5.QtCore import pyqtSignal
from aequilibrae.paths import NetworkSkimming, SkimResults
from aequilibrae.utils.worker_thread import WorkerThread


class TSPProcedure(WorkerThread):
    finished = pyqtSignal(object)

    def __init__(self, parentThread, graph, depot, vehicles):
        WorkerThread.__init__(self, parentThread)
        self.graph = graph
        self.depot = depot
        self.vehicles = vehicles
        self.error = None
        self.mult = 100
        self.report = []
        self.node_sequence = []

    def doWork(self):
        from ortools.constraint_solver import pywrapcp
        from ortools.constraint_solver import routing_enums_pb2

        ns = NetworkSkimming(self.graph)
        ns.execute()

        skm = ns.results.skims
        mat = (skm.get_matrix(skm.names[0]) * self.mult).astype(int)
        self.depot = list(skm.index).index(self.depot)
        # Create the routing index manager.
        manager = pywrapcp.RoutingIndexManager(mat.shape[0], self.vehicles, self.depot)

        # Create Routing Model.
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            """Returns the distance between the two nodes."""
            # Convert from routing variable Index to distance matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)

            return mat[from_node, to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)

        # Define cost of each arc.
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Setting first solution heuristic.
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

        # Solve the problem.
        solution = routing.SolveWithParameters(search_parameters)

        # Print solution on console.
        if not solution:
            self.error = "Solution not found"
            self.report.append(self.error)
        else:
            self.report.append(f"Objective function value: {solution.ObjectiveValue() / self.mult}")
            index = routing.Start(0)
            plan_output = "Route:\n"
            route_distance = 0

            while not routing.IsEnd(index):
                p = skm.index[manager.IndexToNode(index)]
                self.node_sequence.append(p)
                plan_output += f" {p} ->"
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)

            p = skm.index[manager.IndexToNode(index)]
            self.node_sequence.append(p)
            plan_output += f" {p}\n"
            self.report.append(plan_output)
        self.finished.emit("TSP")

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from os.path import join
from aequilibrae.paths import NetworkSkimming, SkimResults

from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *
from ..common_tools.worker_thread import WorkerThread


class TSPProcedure(WorkerThread):
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
        res = SkimResults()
        res.prepare(self.graph)

        ns = NetworkSkimming(self.graph, res)
        ns.execute()

        skm = res.skims
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
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

        # Solve the problem.
        solution = routing.SolveWithParameters(search_parameters)

        # Print solution on console.
        if not solution:
            self.error = 'Solution not found'
            self.report.append(self.error)
        else:
            self.report.append(f'Objective: {solution.ObjectiveValue() / self.mult}')
            index = routing.Start(0)
            plan_output = 'Route:\n'
            route_distance = 0

            while not routing.IsEnd(index):
                p = skm.index[manager.IndexToNode(index)]
                self.node_sequence.append(p)
                plan_output += f' {p} ->'
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)

            self.node_sequence.append(skm.index[manager.IndexToNode(index)])
            plan_output += f' {manager.IndexToNode(index)}\n'
            self.report.append(plan_output)
        self.finished_threaded_procedure.emit("TSP")

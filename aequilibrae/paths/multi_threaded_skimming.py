import numpy as np


class MultiThreadedNetworkSkimming:
    def __init__(self):
        self.predecessors = None  # The predecessors for each node in the graph
        self.temporary_skims = None  # holds the skims for all nodes in the network (during path finding)
        self.reached_first = None    # Keeps the order in which the nodes were reached for the cascading network loading
        self.connectors = None  # The previous link for each node in the tree
        self.temp_b_nodes = None  #  holds the b_nodes in case of flows through centroid connectors are blocked

    # In case we want to do by hand, we can prepare each method individually
    def prepare(self, graph, results):
        self.predecessors = np.zeros((results.nodes, results.cores), dtype=np.int32)
        self.temporary_skims = np.zeros((results.nodes, results.num_skims, results.cores), dtype=np.float64)
        self.reached_first = np.zeros((results.nodes, results.cores), dtype=np.int32)
        self.connectors = np.zeros((results.nodes, results.cores), dtype=np.int32)
        self.temp_b_nodes = graph.b_node.copy()
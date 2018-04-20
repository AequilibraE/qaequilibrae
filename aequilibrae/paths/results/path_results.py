import numpy as np
from ..graph import Graph

class PathResults:
    def __init__(self):
        """
        @type graph: Set of numpy arrays to store Computation results
        """
        self.predecessors = None
        self.connectors = None
        self.skims = None
        self.path = None
        self.path_nodes = None
        self.milepost = None
        self.reached_first = None
        self.origin = None
        self.destination = None

        self.links = -1
        self.nodes = -1
        self.zones = -1
        self.num_skims = -1
        self.__integer_type = None
        self.__float_type = None
        self.__graph_id__ = None

    def prepare(self, graph):
        self.__integer_type = graph.default_types('int')
        self.__float_type = graph.default_types('float')
        self.nodes = graph.num_nodes + 1
        self.zones = graph.centroids + 1
        self.links = graph.num_links + 1
        self.num_skims = graph.skims.shape[1]

        self.predecessors = np.zeros(self.nodes, dtype=self.__integer_type)
        self.connectors = np.zeros(self.nodes, dtype=self.__integer_type)
        self.reached_first = np.zeros(self.nodes, dtype=self.__integer_type)
        self.skims = np.zeros((self.nodes, self.num_skims), self.__float_type)
        self.__graph_id__ = graph.__id__

    def reset(self):
        if self.predecessors is not None:
            self.predecessors.fill(-1)
            self.connectors.fill(-1)
            self.skims.fill(np.inf)
            self.path = None
            self.path_nodes = None
            self.milepost = None

        else:
            print 'Exception: Path results object was not yet prepared/initialized'

    def update_trace(self, graph, destination):
        # type: (Graph, int) -> (None)

        if self.__graph_id__ != graph.__id__:
            raise ValueError("Results prepared for a different Graph")

        if not isinstance(destination, int):
            raise TypeError('Destination needs to be an integer')
        if not isinstance(graph, Graph):
            raise TypeError('graph needs to be an AequilibraE Graph')
        if destination >= graph.nodes_to_indices.shape[0]:
            raise ValueError('destination out of the range of node numbers in the graph')

        dest_index = graph.nodes_to_indices[destination]
        origin_index = graph.nodes_to_indices[self.origin]

        self.destination = destination
        self.milepost = None
        self.path_nodes = None
        if self.predecessors[dest_index] > 0:
            all_connectors = []
            all_nodes = [dest_index]
            mileposts = []
            p = dest_index
            if p != origin_index:
                while p != origin_index:
                    p = self.predecessors[p]
                    connector = self.connectors[dest_index]
                    all_connectors.append(graph.graph['link_id'][connector])
                    mileposts.append(graph.cost[connector])
                    all_nodes.append(p)
                    dest_index = p
                self.path = np.asarray(all_connectors, graph.default_types('int'))[::-1]
                self.path_nodes = graph.all_nodes[np.asarray(all_nodes, graph.default_types('int'))][::-1]
                mileposts.append(0)
                self.milepost = np.cumsum(mileposts[::-1])

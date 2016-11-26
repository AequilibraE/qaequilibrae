# cimport numpy as np
# cimport cython
# import multiprocessing as M
# include 'parameters.pxi'
import numpy as np


class PathResults:
    def __init__(self):
        """
        @type graph: Set of numpy arrays to store Computation results
        """
        self.predecessors = None
        self.connectors = None
        self.temporary_skims = None
        self.path = None
        self.pathnodes = None
        self.milepost = None

        self.links = -1
        self.nodes = -1
        self.zones = -1
        self.num_skims = -1
        self.__graph_id__ = None

    def prepare(self, graph):

        self.nodes = graph.num_nodes + 1
        self.zones = graph.centroids + 1
        self.links = graph.num_links + 1
        self.num_skims = graph.skims.shape[1]

        self.predecessors = np.zeros(self.nodes, dtype=np.int32)
        self.connectors = np.zeros(self.nodes, dtype=np.int32)
        self.temporary_skims = np.zeros((self.nodes, self.num_skims), np.float64)
        self.__graph_id__ = graph.__id__

    def reset(self):
        if self.predecessors is not None:
            self.predecessors.fill(-1)
            self.connectors.fill(-1)
            self.temporary_skims.fill(0)
            self.path = None
            self.path_nodes = None
            self.milepost = None

        else:
            print 'Exception: Path results object was not yet prepared/initialized'

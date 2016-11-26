# cimport numpy as np
# cimport cython
# include 'parameters.pxi'
import multiprocessing as mp
import numpy as np
import warnings
import tempfile

class AssignmentResults:
    def __init__(self):
        """
        @type graph: Set of numpy arrays to store Computation results
        self.critical={required:{"links":[lnk_id1, lnk_id2, ..., lnk_idn], "path file": False}, results:{}}
        """
        self.link_loads = None   # The actual results for assignment
        self.predecessors = None  # The predecessors for each node in the graph
        self.connectors = None  # The previous link for each node in the tree
        self.skims = None  # The array of skims
        self.no_path = None  # The list os paths
        self.temporary_skims = None
        self.num_skims = None  # number of skims that will be computed. Depends on the setting of the graph provided
        self.cores = mp.cpu_count()
        self.critical = {"parameters":{},
                         "queries": {},     # Queries are a dictionary
                         "results": {}}
        self.set_critical_storage_parameters(memory=True, compression=False)


        self.path_file = {"save": False,
                          "results": None,
                          "output": None}

        self.temp_dir = tempfile.gettempdir()

        self.nodes = -1
        self.zones = -1
        self.links = -1
        self.__graph_id__ = None


    # In case we want to do by hand, we can prepare each method individually
    def prepare(self, graph):

        self.nodes = graph.num_nodes + 1
        self.zones = graph.centroids + 1
        self.links = graph.num_links + 1
        self.num_skims = graph.skims.shape[1]
        self.__redim()
        self.__graph_id__ = graph.__id__

    def reset(self):
        if self.predecessors is not None:
            self.predecessors.fill(-1)
            self.connectors.fill(-1)
            self.skims.fill(0)
            self.no_path.fill(-1)
        else:
            print 'Exception: Assignment results object was not yet prepared/initialized'

    def __redim(self):
        self.link_loads = np.zeros((self.links, self.cores), np.float64)
        self.predecessors = np.zeros((self.nodes, self.cores), dtype=np.int32)
        self.connectors = np.zeros((self.nodes, self.cores), dtype=np.int32)

        self.skims = np.zeros((self.zones, self.zones, self.num_skims), np.float64)
        self.no_path = np.zeros((self.zones, self.zones, self.cores), dtype=np.int32)
        self.temporary_skims = np.zeros((self.nodes, self.num_skims, self.cores), np.float64)

        self.reset()

    def set_cores(self, cores):
        if isinstance(cores, int):
            if cores > 0:
                if self.cores != cores:
                    self.cores = cores
                    if self.predecessors is not None:
                        self.__redim()
            else:
                raise ValueError("Number of cores needs to be equal or bigger than one")
        else:
            raise ValueError("Number of cores needs to be an integer")

    def set_critical_storage_parameters(self, memory=None, compression=None):
        if memory is not None:
            self.critical['parameters']['memory'] = memory

        if compression is not None:
            self.critical['parameters']['compression'] = compression

    def SetCriticalOutput(self, ):
        # Warning for the select link analysis in memory
        if self.critical['parameters']['memory']:
            warnings.warn("Warning...........Message")

    def setSavePathFile(self, save=False, path_result=None):
        self.path_file["save"] = save
        if save:
            if self.nodes > 0 and self.zones > 0:
                self.path_file["results"] = np.memmap(path_result, dtype=np.int32, mode='w+', shape=(self.zones,self.nodes, 2))
                print self.zones, self.nodes, 2
        else:
            self.path_file["results"] = np.zeros(self.zones, 1, 2)

    def setTempDir(self, temp_dir):
        self.temp_dir = temp_dir

    def results(self):
        return np.sum(self.link_loads, axis=1)


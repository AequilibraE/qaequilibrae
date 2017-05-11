import sys
sys.path.append('/home/pedro/.qgis2/python/plugins/AequilibraE')
import numpy as np
import os
from scipy.sparse import csr_matrix


# The graph
from aequilibrae.paths import Graph
import aequilibrae as ae

# The results for assignment and shortest path
from aequilibrae.paths.results import PathResults
from aequilibrae.paths.results import AssignmentResults


#loading the graph prepared in QGIS
my_graph = Graph()
my_graph.load_from_disk('/home/pedro/test.aeg')
my_graph.set_graph(centroids=3220, cost_field='length', block_centroid_flows=False)

my_graph.prepare_graph()
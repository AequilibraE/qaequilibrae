# The graph
from aequilibrae.paths import Graph
import os
import numpy as np

path_files = '/media/pedro/LargeDrive/GOOGLE_DRIVES/UCI/DATA/Pedro/AequilibraE/Testing data/Assignment'
network_layer = 'final_sydney_network.shp'

reference_graph = 'SydneyGraph.aeg'

# Create graph with geography file
my_graph = Graph()
my_graph.create_from_geography(os.path.join(path_files, network_layer),
                               id_field='link_ID',
                               dir_field='direction',
                               cost_field='Length2')

my_graph.set_graph(centroids=393,
                   cost_field='length2',
                   block_centroid_flows=True)

# Loads reference graph
ref_graph = Graph()
ref_graph.load_from_disk(os.path.join(path_files, reference_graph))

#check fields in the graph
if list(my_graph.graph.dtype.fields.keys()).sort() != list(ref_graph.graph.dtype.fields.keys()).sort():
    print my_graph.graph.dtype.fields.keys().sort()
    print ref_graph.graph.dtype.fields.keys().sort()
    raise ValueError('Fields in graph are not consistent')
    sys.exit(1)

for i in list(my_graph.graph.dtype.fields.keys()):
    test = np.array_equal(my_graph.graph[i], ref_graph.graph[i])
    if not test:
        raise ValueError('Differences on graph. Field ' + i)
        sys.exit(1)
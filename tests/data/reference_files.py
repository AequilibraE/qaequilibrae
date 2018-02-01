import tempfile
from os.path import dirname, abspath, join

# For the graph tests
test_network = join(dirname(dirname(abspath(__file__))),'data' ,'Final_Network.shp')
test_graph = join(dirname(dirname(abspath(__file__))),'data' ,'test_graph.aeg')
path_test = tempfile.gettempdir()

# For the skimming test
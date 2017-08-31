import os, sys
from unittest import TestCase
from aequilibrae.paths import Graph
from aequilibrae.paths.results import SkimResults
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import skimming_single_origin
from aequilibrae.paths.multi_threaded_skimming import MultiThreadedNetworkSkimming

# Adds the folder with the data to the path and collects the paths to the files
lib_path = os.path.abspath(os.path.join('..', '..'))
sys.path.append(lib_path)
from data import path_test, test_graph


class TestSkimming_single_origin(TestCase):
    def test_skimming_single_origin(self):


        # graph
        g = Graph()
        g.load_from_disk(test_graph)
        g.set_graph(centroids=29, cost_field='distance', skim_fields=None)
        # None implies that only the cost field will be skimmed


        # matrix
        a = AequilibraeMatrix(cores=1,
                              zones=g.centroids+1,
                              names=['test_skimming']
                              )
        g.storage_path = os.path.join(path_test, 'aequilibrae_skimming_test.aem')


        # skimming results
        res = SkimResults()
        res.prepare(g)
        aux_result = MultiThreadedNetworkSkimming()
        aux_result.prepare(g, res)

        print res.skims.matrix_view.shape[:]
        res.skims.matrix_view[1,:,:]=1
        for x in range(30):
            for y in range(1):
                res.skims.matrix_view[1,x,y]=1.1
        # skimming_single_origin(1, g, res, aux_result, 0)

        # print res.skims.matrix_view[1,:,:]
        # self.fail('Skimming returned an error')

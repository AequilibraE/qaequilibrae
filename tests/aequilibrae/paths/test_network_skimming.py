import os, sys
from unittest import TestCase
from aequilibrae.paths import Graph
from aequilibrae.paths.results import SkimResults
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import network_skimming
import numpy as np

# Adds the folder with the data to the path and collects the paths to the files
lib_path = os.path.abspath(os.path.join('..', '..'))
sys.path.append(lib_path)
from data import path_test, test_graph

from parameters_test import centroids


class TestNetwork_skimming(TestCase):
    def test_network_skimming(self):
        # graph
        g = Graph()
        g.load_from_disk(test_graph)
        g.set_graph(centroids=centroids, cost_field='distance', skim_fields=None)
        # None implies that only the cost field will be skimmed

        # skimming results
        res = SkimResults()
        res.prepare(g)

        a = network_skimming(g, res)

        tot = np.sum(res.skims.distance[:, :])

        if tot > 10e10:
            self.fail('Skimming was not successful. At least one np.inf returned.')

        if a:
            self.fail('Skimming returned an error:' + str(a))

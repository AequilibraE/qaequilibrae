from unittest import TestCase
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import all_or_nothing, Graph, AssignmentResults
import sys, os
import numpy as np

# Adds the folder with the data to the path and collects the paths to the files
lib_path = os.path.abspath(os.path.join('..', '..'))
sys.path.append(lib_path)
from data import path_test, test_graph


class TestAll_or_nothing(TestCase):
    def test_all_or_nothing(self):

        # Loads and prepares the graph
        g = Graph()
        g.load_from_disk(test_graph)
        g.set_graph(cost_field='distance', skim_fields=None)
        # None implies that only the cost field will be skimmed


        # Prepares the matrix for assignment
        args = {'file_name': '/tmp/my_matrix.aem',
                'zones': g.num_zones,
                'matrix_names': ['mat'],
                'index_names': ['my indices']}

        matrix = AequilibraeMatrix()
        matrix.create_empty(**args)

        matrix.index[:] = g.centroids[:]
        matrix.mat.fill(1)
        matrix.computational_view(['mat'])

        # Performs assignment
        res = AssignmentResults()
        res.prepare(g, matrix)

        all_or_nothing(matrix, g, res)
        res.save_to_disk(output_file_name='/tmp/link_loads.aed', file_type='aed')
        self.fail('Assignment failed')

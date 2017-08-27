from unittest import TestCase

from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.distribution import GravityCalibration
import numpy as np

zones = 100

# Impedance matrix_procedures
args = {'zones': zones,
        'cores': 1,
        'names': ['impedance']}

impedance = AequilibraeMatrix(**args)
impedance.impedance[:, :] = np.random.rand(zones, zones)[:,:]  * 1000
impedance.index[:] = np.arange(impedance.zones) + 100
impedance.computational_view(['impedance'])

args['names'] = ['matrix']
matrix = AequilibraeMatrix(**args)
matrix.matrix[:, :] = np.random.rand(zones, zones)[:,:]  * 1000
matrix.index[:] = np.arange(matrix.zones) + 100
matrix.computational_view(['matrix'])



class TestGravityCalibration(TestCase):
    def test_calibrate(self):
        args = {'impedance': impedance,
                'matrix': matrix,
                'function': 'expo'}

        distributed_matrix = GravityCalibration(**args)
        distributed_matrix.calibrate()
        if distributed_matrix.gap > 0.0001:
            self.fail('Calibration did not converge')

    def test_check_inputs(self):
        # self.fail()
        pass

    def test_apply_gravity(self):
        # self.fail()
        pass

    def test_get_parameters(self):
        # self.fail()
        pass

from unittest import TestCase
from aequilibrae.distribution import SyntheticGravityModel

class TestSyntheticGravityModel(TestCase):
    def test_load(self):
        a = SyntheticGravityModel()
        a.function = 'EXPO'
        a.beta = 0.1
        self.assertEqual(a.function, 'EXPO') # Did we save the value?

        a.function = 'POWER'
        # Check if we zeroed the parameters when changing the function
        self.assertEqual(a.beta, None)
        a.alpha = 0.1


import unittest

from qgis.core import QgsProviderRegistry

from .utilities import get_qgis_app


class QGISTest(unittest.TestCase):
    """Test the QGIS Environment"""

    def setUp(self) -> None:
        _ = get_qgis_app()

    def test_qgis_environment(self):
        """QGIS environment has the expected providers"""

        prov_reg = QgsProviderRegistry.instance()
        self.assertGreater(len(prov_reg.providerList()), 20, "Missing too many providers")
        self.assertIn("spatialite", prov_reg.providerList())

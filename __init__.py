# This portion of the script initializes the plugin, making it known to QGIS.
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "aequilibrae")))


def classFactory(iface):
    from .AequilibraEMenu import AequilibraEMenu

    return AequilibraEMenu(iface)

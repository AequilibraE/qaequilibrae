# This portion of the script initializes the plugin, making it known to QGIS.
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "aequilibrae")))


def classFactory(iface):
    from modules.common_tools import starts_logging

    starts_logging()
    from .AequilibraEMenu import AequilibraEMenu

    return AequilibraEMenu(iface)

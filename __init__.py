# This portion of the script initializes the plugin, making it known to QGIS.
import os
import sys
from os.path import abspath, join, dirname

sys.path.append(join(os.path.dirname(__file__), "packages"))


def classFactory(iface):
    from .aequilibrae_menu import AequilibraEMenu
    return AequilibraEMenu(iface)

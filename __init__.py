# This portion of the script initializes the plugin, making it known to QGIS.
import sys
import os
from os.path import abspath, join, dirname

from .download_extra_packages_class import download_all

sys.path.append(join(os.path.dirname(__file__), "packages"))
download_all().install()

def classFactory(iface):
    from .aequilibrae_menu import AequilibraEMenu

    return AequilibraEMenu(iface)

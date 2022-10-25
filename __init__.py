# This portion of the script initializes the plugin, making it known to QGIS.
import sys
from os.path import abspath, join, dirname

from .download_extra_packages_class import download_all

da = download_all()
da.install()


def classFactory(iface):
    from .aequilibrae_menu import AequilibraEMenu

    return AequilibraEMenu(iface)

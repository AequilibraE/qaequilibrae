"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       QGIS plugin initializer
 Purpose:    Initialize plugin

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

# This portion of the script initializes the plugin, making it known to QGIS.
import sys
from .aequilibrae.__version__ import release_version as version

sys.dont_write_bytecode = True

sys.path.append("C:/Users/Pedro/.qgis2/python/plugins/AequilibraE/")


def classFactory(iface):
    from AequilibraEMenu import AequilibraEMenu
    return AequilibraEMenu(iface)






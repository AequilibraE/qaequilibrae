"""
/***************************************************************************
 AequilibraE - www.aequilibrae.com
 
    Name:        QGIS plugin initializer
                              -------------------
        begin                : 2014-03-19
        copyright            : AequilibraE developers 2014
        Original Author: Pedro Camargo pedro@xl-optim.com
        Contributors: 
        Licence: See LICENSE.TXT
 ***************************************************************************/

"""

# This portion of the script initializes the plugin, making it known to QGIS.
import sys
sys.dont_write_bytecode = True
sys.path.append("C:/Users/Pedro/.qgis2/python/plugins/AequilibraE/")

def classFactory(iface):
    from AequilibraE_menu import AequilibraE_menu
    return AequilibraE_menu(iface)






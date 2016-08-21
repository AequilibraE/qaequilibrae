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

from . import paths  # We import the graph
from . import distribution
# from .assignment import *
# from . import results

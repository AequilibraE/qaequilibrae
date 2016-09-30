"""
=============
path computation related code
=============

"""
__author__ = "Pedro Camargo ($Author: Pedro Camargo $)"
__version__ = "1.0"
__revision__ = "$Revision: 1 $"
__date__ = "$Date: 2016-07-02$"

from .graph import Graph
from .assignment import all_or_nothing
from .results import *

# We import the algorithms
import platform
plat = platform.system()

if plat == 'Windows':
    import struct
    if (8 * struct.calcsize("P")) == 64:
        from win64 import *

    if (8 * struct.calcsize("P")) == 32:
        from win32 import *

if plat == 'Linux':
    import struct
    if (8 * struct.calcsize("P")) == 64:
        from linux64 import *

if plat == 'Darwin':
    from mac import *

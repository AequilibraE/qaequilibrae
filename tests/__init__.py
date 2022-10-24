# import qgis libs so that ve set the correct sip api version

import qgis  # pylint: disable=W0611  # NOQA
import sys
from os.path import abspath, join, dirname
sys.path.insert(0, abspath(join(dirname(dirname(__file__)), "")))
sys.path.insert(0, abspath(join(dirname(dirname(__file__)), "aequilibrae")))
# import qgis libs so that ve set the correct sip api version

import sys
from os.path import abspath, join, dirname

import qgis  # pylint: disable=W0611  # NOQA

sys.path.insert(0, abspath(join(dirname(dirname(__file__)), "")))

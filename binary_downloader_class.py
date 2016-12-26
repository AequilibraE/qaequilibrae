
from qgis.core import *
import qgis
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
import os

from auxiliary_functions import *

import os
import urllib
import platform
import struct

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/")

from ui_binary_downloader import *

class BinaryDownloaderDialog(QtGui.QDialog, Ui_binary_downloader):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.linux64 = 'http://www.aequilibrae.com/binaries/v.0.3.3/AoN_linux64.so'
        self.linux32 = 'http://www.aequilibrae.com/binaries/v.0.3.3/AoN_linux64.so'
        self.windows32 = 'http://www.aequilibrae.com/binaries/v.0.3.3/AoN_win32.pyd'
        self.windows64 = 'http://www.aequilibrae.com/binaries/v.0.3.3/AoN_win64.pyd'
        self.mac = 'http://www.aequilibrae.com/binaries/v.0.3.3/AoN_mac.so'

        self.local_path = os.path.dirname(os.path.abspath(__file__)) + '/aequilibrae/paths/AoN.so'
        plat = platform.system()
        if plat == 'Windows':
            self.local_path = os.path.dirname(os.path.abspath(__file__)) + '/aequilibrae/paths/AoN.pyd'
            if (8 * struct.calcsize("P")) == 64:
                self.binary_path = self.windows64
            if (8 * struct.calcsize("P")) == 32:
                self.binary_path = self.windows32
        if plat == 'Linux':
            if (8 * struct.calcsize("P")) == 64:
                self.binary_path = self.linux64
        if plat == 'Darwin':
            self.binary_path = self.mac

        self.lbl_remote_path.setText('File download path: ' + self.binary_path)
        self.lbl_local_path.setText('File local destination: ' + self.local_path)
        self.but_download.clicked.connect(self.download_binary)

    def download_binary(self):
        self.but_download.setEnabled(False)
        urllib.urlretrieve(self.binary_path, self.local_path)
        self.close()
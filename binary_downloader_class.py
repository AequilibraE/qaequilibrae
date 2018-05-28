from qgis.core import *
from PyQt4 import uic, QtGui

from .common_tools import ReportDialog
import os
import urllib
import platform
import struct
print os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/forms/", 'ui_binary_downloader.ui')
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__) + "/forms/", 'ui_binary_downloader.ui'))


class BinaryDownloaderDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtGui.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        error = True
        self.linux64 = 'https://goo.gl/V5Zkyv'
        # self.linux32 = 'http://www.aequilibrae.com/binaries/v.0.3.3/AoN_linux64.so'
        self.windows32 = 'https://goo.gl/cA9FDu'
        self.windows64 = 'https://goo.gl/XY3Ri9'
        self.mac = 'https://goo.gl/UFBZjU'

        self.local_path = os.path.dirname(os.path.abspath(__file__)) + '/aequilibrae/paths/AoN.so'
        plat = platform.system()
        if plat == 'Windows':
            self.local_path = os.path.dirname(os.path.abspath(__file__)) + '/aequilibrae/paths/AoN.pyd'
            if (8 * struct.calcsize("P")) == 64:
                self.binary_path = self.windows64
                error = False
            if (8 * struct.calcsize("P")) == 32:
                self.binary_path = self.windows32
                error = False
        if plat == 'Linux':
            if (8 * struct.calcsize("P")) == 64:
                self.binary_path = self.linux64
                error = False
        if plat == 'Darwin':
            self.binary_path = self.mac
            error = False

        if error:
            dlg2 = ReportDialog(self.iface, ['AequilibraE not supported on your platform'])
            dlg2.show()
            dlg2.exec_()
        self.lbl_remote_path.setText('File download path: ' + self.binary_path)
        self.lbl_local_path.setText('File local destination: ' + self.local_path)
        self.but_download.clicked.connect(self.download_binary)

    def download_binary(self):
        self.but_download.setEnabled(False)
        urllib.urlretrieve(self.binary_path, self.local_path)
        self.close()
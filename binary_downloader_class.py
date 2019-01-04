from qgis.core import *
from qgis.PyQt import uic, QtGui, QtWidgets

from .common_tools import ReportDialog
import os
import urllib
import platform
import struct
import yaml
from os.path import dirname, abspath, join
import zipfile

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__) + "/forms/", 'ui_binary_downloader.ui'))


class BinaryDownloaderDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        error = True

        self.local_path = os.path.dirname(os.path.abspath(__file__)) + '/aequilibrae/aequilibrae/paths'

        d = dirname(abspath(__file__))
        with open(os.path.join(d, 'meta.yaml'), 'r') as yml:
            par = yaml.load(yml)

        self.binary_path = par['binary source']
        self.lbl_remote_path.setText('File download path: ' + self.binary_path)
        self.lbl_local_path.setText('File local destination: ' + self.local_path)
        self.but_download.clicked.connect(self.download_binary)

    def download_binary(self):
        self.but_download.setEnabled(False)
        dest_path = join(self.local_path, 'binaries.zip')
        urllib.request.urlretrieve(self.binary_path, dest_path)
        print(dest_path)
        zipfile.ZipFile(dest_path).extractall(self.local_path)
        self.close()
